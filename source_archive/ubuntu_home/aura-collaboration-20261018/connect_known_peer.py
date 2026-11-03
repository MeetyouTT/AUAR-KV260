"""Probe only advertised sync endpoints and prefer an actually reachable TCP endpoint."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import ipaddress
import json
from pathlib import Path
import socket
import subprocess
import urllib.parse
from sync_api import API, alias, utc

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
api = API()
peer = next(row for row in api.config.get('devices', []) if alias(row.get('deviceID')) == '2282e32dda')
identity = peer['deviceID']
discovery = api.call('/rest/system/discovery')
cache = discovery.get('cache', discovery)
entry = cache.get(identity) or {}
addresses = entry.get('addresses') or []
candidates = []
for address in addresses:
    try:
        parsed = urllib.parse.urlparse(address)
        ip = ipaddress.ip_address(parsed.hostname)
        if parsed.scheme == 'tcp' and not ip.is_loopback and not ip.is_link_local and parsed.port:
            candidates.append(address)
    except (ValueError, TypeError):
        continue


def probe(address):
    parsed = urllib.parse.urlparse(address)
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=2):
            result = 'CONNECTED'
    except Exception as error:
        result = type(error).__name__
    return address, result


with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(probe, candidates))
report = {'observed_utc': utc(), 'name': peer.get('name'), 'probes': []}
for address, result in results:
    host = urllib.parse.urlparse(address).hostname
    private = ipaddress.ip_address(host).is_private
    report['probes'].append({'address': address if private else '[advertised public endpoint]',
                             'status': result, 'private': private})
success = [address for address, result in results if result == 'CONNECTED']
success.sort(key=lambda address: not ipaddress.ip_address(urllib.parse.urlparse(address).hostname).is_private)
if success and args.apply:
    previous = list(peer.get('addresses') or [])
    combined = list(dict.fromkeys(success+previous+['dynamic']))
    command = ['/home/ghmd/.local/opt/verysync/verysync', 'cli', 'config', 'devices', identity, 'addresses', 'set', *combined]
    backup = Path(__file__).resolve().parent/'peer-address-backup.json'
    with backup.open('x', encoding='utf-8') as stream:
        json.dump({'peer_alias': alias(identity), 'addresses': previous}, stream)
    backup.chmod(0o600)
    process = subprocess.run(command, capture_output=True, text=True, timeout=15)
    report['address_update_success'] = process.returncode == 0
    if process.returncode:
        raise RuntimeError('Could not update known peer addresses; no secrets printed')
elif args.apply:
    report['address_update_success'] = False
    report['reason'] = 'No advertised TCP endpoint is currently reachable; existing dynamic configuration retained'
else:
    help_text = subprocess.run(['/home/ghmd/.local/opt/verysync/verysync', 'cli', 'config', 'devices', identity,
                                'addresses', 'set', '--help'], capture_output=True, text=True, timeout=15)
    report['control_usage'] = help_text.stdout.replace(identity, alias(identity))
target = Path(__file__).resolve().parent/('peer-connect-'+str(__import__('time').time_ns())+'.json')
target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
