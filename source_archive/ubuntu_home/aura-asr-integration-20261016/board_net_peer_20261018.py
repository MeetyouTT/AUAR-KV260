"""Check the existing board Ethernet peer without changing configuration."""
import datetime
import json
from pathlib import Path
import socket
import subprocess
import urllib.request


def run(args):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=6)
        return {'code': p.returncode, 'output': p.stdout[-4000:]}
    except Exception as exc:
        return {'error': type(exc).__name__ + ': ' + str(exc)}


peer = '192.168.50.1'
result = {
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'hostname': socket.gethostname(),
    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'addresses': run(['ip', '-br', 'addr']),
    'link': run(['ip', '-br', 'link', 'show', 'eth0']),
    'route_to_peer': run(['ip', 'route', 'get', peer]),
    'neighbors_before': run(['ip', 'neigh', 'show', 'dev', 'eth0']),
}
result['ping'] = run(['ping', '-I', 'eth0', '-c', '2', '-W', '1', peer])
result['tcp'] = {}
for port in (22, 445, 8791):
    try:
        with socket.create_connection((peer, port), timeout=1.5):
            result['tcp'][str(port)] = 'connected'
    except Exception as exc:
        result['tcp'][str(port)] = type(exc).__name__ + ': ' + str(exc)
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://' + peer + ':8791/health', timeout=2) as response:
        data = response.read(8193)
        result['asr_health'] = {'status': response.status,
                                'body': data[:8192].decode('utf-8', 'replace')}
except Exception as exc:
    result['asr_health'] = {'error': type(exc).__name__ + ': ' + str(exc)}
result['neighbors_after'] = run(['ip', 'neigh', 'show', 'dev', 'eth0'])
print(json.dumps(result, ensure_ascii=False))
