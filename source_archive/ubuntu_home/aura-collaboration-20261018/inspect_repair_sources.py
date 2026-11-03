"""Inspect advertised LAN endpoints and candidate reuse metadata, without mutation."""
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
from pathlib import Path
import socket
import urllib.parse
from sync_api import API, alias, rows, utc

api = API()
names = api.names()
report = {'observed_utc': utc(), 'devices': [], 'discovery': [], 'sample_file_metadata': []}
for row in rows(api.config.get('devices', [])):
    report['devices'].append({'alias': alias(row.get('deviceID', row.get('deviceId'))),
        'name': row.get('name'), 'addresses': [address for address in row.get('addresses', [])
                                              if address == 'dynamic' or '172.23.' in address or '192.168.' in address],
        'paused': row.get('paused')})
try:
    discovery = api.call('/rest/system/discovery')
    report['discovery_response_type'] = type(discovery).__name__
    if isinstance(discovery, dict):
        report['discovery_top_keys'] = [key for key in discovery if key in ('cache', 'errors', 'methods')]
    cache = discovery.get('cache', discovery) if isinstance(discovery, dict) else {}
    candidates = []
    for peer, record in cache.items():
        if peer not in names:
            continue
        addresses = record.get('addresses', []) if isinstance(record, dict) else []
        for address in addresses:
            try:
                parsed = urllib.parse.urlparse(address)
                host, port = parsed.hostname, parsed.port
                ip = ipaddress.ip_address(host)
                if ip.is_private and not ip.is_loopback and not ip.is_link_local and parsed.scheme == 'tcp':
                    candidates.append((peer, host, port))
            except (ValueError, TypeError):
                continue
    def probe(candidate):
        peer, host, port = candidate
        try:
            with socket.create_connection((host, port), timeout=2):
                status = 'TCP_CONNECTED'
        except Exception as error:
            status = type(error).__name__
        return {'name': names[peer], 'alias': alias(peer), 'address': 'tcp://'+host+':'+str(port), 'status': status}
    with ThreadPoolExecutor(max_workers=6) as pool:
        report['discovery'] = list(pool.map(probe, candidates))
except RuntimeError as error:
    report['discovery_error'] = str(error)
folder = next(row for row in api.folders() if alias(api.identity(row)) == '04087ac86d')
identity = api.identity(folder)
need = api.call('/rest/db/need', {'folder': identity, 'page': 1, 'perpage': 10000})
entries = [row for group in ('progress', 'queued', 'rest') for row in need.get(group) or []]
report['remaining_files'] = len(entries)
for relative in ['语音共享文件/aura/models/tts/OmniVoice/model.safetensors',
                 '共享文件夹/aura/models/tts/OmniVoice/model.safetensors']:
    value = api.call('/rest/db/file', {'folder': identity, 'file': relative})
    report['sample_file_metadata'].append({'path': relative,
        'global': value.get('global'), 'local': value.get('local')})
target = Path(__file__).resolve().parent/'repair-inspection.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
for row in report['sample_file_metadata']:
    for kind in ('global', 'local'):
        value = row.get(kind) or {}
        row[kind] = {key: value.get(key) for key in ('size', 'modified', 'modifiedS', 'modifiedNs', 'blockSize',
                                                      'blocksHash', 'permissions', 'deleted', 'invalid', 'numBlocks')}
print(json.dumps(report, ensure_ascii=False, indent=2))
