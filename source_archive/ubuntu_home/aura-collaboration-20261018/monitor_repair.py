"""Observe repair convergence and optional exact probe-file availability."""
import argparse
import json
from pathlib import Path
import time
from sync_api import API, alias, rows, utc

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--samples', type=int, default=3)
parser.add_argument('--probe')
parser.add_argument('--scan-voice', action='store_true')
args = parser.parse_args()
api = API()
names = api.names()
report = {'samples': []}
if args.scan_voice:
    report['scans'] = []
    for folder in api.folders():
        try:
            response = api.call('/rest/db/scan', {'folder': api.identity(folder), 'sub': '语音共享文件'},
                                method='POST', timeout=20)
            report['scans'].append({'folder_alias': alias(api.identity(folder)), 'result': response})
        except RuntimeError as error:
            report['scans'].append({'folder_alias': alias(api.identity(folder)), 'error': str(error)})
for index in range(args.samples):
    if index:
        time.sleep(10)
    connections = api.call('/rest/system/connections').get('connections', {})
    sample = {'utc': utc(), 'folders': []}
    for folder in api.folders():
        identity = api.identity(folder)
        status = api.call('/rest/db/status', {'folder': identity})
        value = {'alias': alias(identity), 'paused': folder.get('paused'),
                 **{key: status.get(key) for key in ('state', 'needTotalItems', 'needBytes', 'errors', 'pullErrors')}}
        value['peers'] = []
        if status.get('errors') or status.get('pullErrors'):
            errors = api.call('/rest/folder/errors', {'folder': identity})
            value['error_details'] = [{key: row.get(key) for key in ('path', 'error')}
                                      for row in (errors.get('errors') or [])[:20]]
        for member in rows(folder.get('devices', [])):
            peer = member.get('deviceID', member.get('deviceId'))
            if peer not in connections:
                continue
            completion = api.call('/rest/db/completion', {'folder': identity, 'device': peer})
            value['peers'].append({'name': names.get(peer, ''), 'connected': connections[peer].get('connected'),
                                   **{key: completion.get(key) for key in ('completion', 'needItems', 'needBytes', 'remoteState')}})
        if args.probe:
            info = api.call('/rest/db/file', {'folder': identity, 'file': args.probe})
            available = [item.get('id', item.get('deviceID')) for item in info.get('availability') or []
                         if isinstance(item, dict) and not item.get('fromTemporary')]
            value['probe_current_index_on'] = [names.get(peer, '') for peer in available]
            value['probe_local_global_hash_equal'] = ((info.get('local') or {}).get('blocksHash') ==
                                                       (info.get('global') or {}).get('blocksHash'))
        if status.get('needTotalItems'):
            need = api.call('/rest/db/need', {'folder': identity, 'page': 1, 'perpage': 200})
            value['pending'] = [{key: row.get(key) for key in ('name', 'size', 'type')}
                                for group in ('progress', 'queued', 'rest') for row in need.get(group) or []]
        sample['folders'].append(value)
    report['samples'].append(sample)
    display = {'utc': sample['utc'], 'folders': [{key: value for key, value in row.items() if key != 'pending'}
                                               for row in sample['folders']]}
    print(json.dumps(display, ensure_ascii=False), flush=True)
path = Path(__file__).resolve().parent/('repair-status-'+str(time.time_ns())+'.json')
path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'saved': str(path)}), flush=True)
