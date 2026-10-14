"""Build a GL.iNet plain-text subscription from selected itdog lists."""
import ipaddress
import json
import re
import urllib.request
from pathlib import Path

BASE = 'https://raw.githubusercontent.com/itdoginfo/allow-domains/main/'
SOURCES = (
    [f'Categories/{name}.lst' for name in ('anime', 'block', 'geoblock', 'news', 'porn')]
    + [f'Services/{name}.lst' for name in ('discord', 'hdrezka', 'meta', 'telegram', 'tiktok', 'twitter', 'youtube', 'google_ai', 'roblox')]
    + [f'Subnets/IPv4/{name}.lst' for name in ('discord', 'meta', 'telegram', 'twitter', 'google_meet', 'roblox')]
)

def fetch_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'flint-vpn-list'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)

def extra_networks():
    # Follow the same JSON sources selected by b4geoip, without executing its code.
    config = fetch_json('https://raw.githubusercontent.com/DanielLavrushin/b4geoip/main/config.json')
    selected = {'github', 'bungie', 'sony', 'ubisoft'}
    result = set()
    found = set()
    for item in config['input']:
        args = item.get('args', {})
        name = args.get('name')
        if name not in selected:
            continue
        if item['type'] != 'json' or item.get('action') != 'add':
            raise ValueError(f'Unsupported upstream source for {name}')
        url = args['uri']
        if not url.startswith(('https://api.github.com/', 'https://stat.ripe.net/')):
            raise ValueError(f'Unexpected source URL: {url}')
        data = fetch_json(url)
        values = []
        for path in args['jsonPath']:
            if path == 'data.prefixes.#.prefix':
                values.extend(row['prefix'] for row in data['data']['prefixes'])
            elif '.' not in path and isinstance(data.get(path), list):
                values.extend(data[path])
            else:
                raise ValueError(f'Unsupported JSON path: {path}')
        current = set()
        for value in values:
            network = ipaddress.ip_network(value, strict=False)
            if network.version == 4:
                current.add(str(network))
        if not current:
            print(f'No IPv4 prefixes: {name}, {url}; checking other sources')
            continue
        print(f'b4geoip/{name}: {len(current)} from {url}')
        found.add(name)
        result.update(current)
    if found != selected:
        raise ValueError(f'Missing categories: {selected - found}')
    return result

def normalize(line):
    value = line.split('#', 1)[0].strip().lower()
    if not value or value == '.ua':
        return None
    if '/' in value:
        network = ipaddress.ip_network(value, strict=False)
        if network.version != 4:
            raise ValueError(f'Unexpected IPv6: {value}')
        return str(network)
    value = value.encode('idna').decode('ascii')
    labels = value.split('.')
    if len(labels) < 2 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels):
        raise ValueError(f'Unsupported entry: {value}')
    return value

def main():
    entries = set()
    for source in SOURCES:
        request = urllib.request.Request(BASE + source, headers={'User-Agent': 'flint-vpn-list'})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read().decode('utf-8-sig')
        current = {entry for line in content.splitlines() if (entry := normalize(line))}
        if not current:
            raise ValueError(f'Empty source: {source}')
        print(f'{source}: {len(current)}')
        entries.update(current)
    entries.update(extra_networks())
    target = Path(__file__).with_name('vpn-list.txt')
    temporary = target.with_suffix('.tmp')
    temporary.write_text('\n'.join(sorted(entries)) + '\n', encoding='utf-8')
    temporary.replace(target)
    print(f'Total: {len(entries)}')

if __name__ == '__main__':
    main()
