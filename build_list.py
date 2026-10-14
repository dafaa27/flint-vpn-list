"""Build a GL.iNet plain-text subscription from selected itdog lists."""
import ipaddress
import re
import urllib.request
from pathlib import Path

BASE = 'https://raw.githubusercontent.com/itdoginfo/allow-domains/main/'
SOURCES = (
    [f'Categories/{name}.lst' for name in ('anime', 'block', 'geoblock', 'news', 'porn')]
    + [f'Services/{name}.lst' for name in ('discord', 'hdrezka', 'meta', 'telegram', 'tiktok', 'twitter', 'youtube')]
    + [f'Subnets/IPv4/{name}.lst' for name in ('discord', 'meta', 'telegram', 'twitter', 'google_meet')]
)

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
    target = Path(__file__).with_name('vpn-list.txt')
    temporary = target.with_suffix('.tmp')
    temporary.write_text('\n'.join(sorted(entries)) + '\n', encoding='utf-8')
    temporary.replace(target)
    print(f'Total: {len(entries)}')

if __name__ == '__main__':
    main()
