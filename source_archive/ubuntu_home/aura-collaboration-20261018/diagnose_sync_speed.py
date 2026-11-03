"""Read-only sampled Verysync performance diagnosis; never export configuration secrets."""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

ROOT = Path('/home/ghmd/Win共享文件')
WORK = Path(__file__).resolve().parent
BINARY = '/home/ghmd/.local/opt/verysync/verysync'


def rows(value):
    return value if isinstance(value, list) else list(value.values()) if isinstance(value, dict) else []


def select(value, keys):
    return {key: value[key] for key in keys if key in value}


def alias(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:10]


def category(name):
    parts = name.replace('\\', '/').split('/')
    for component in parts:
        if component.startswith(('.venv', 'venv-', 'host-env')) or component in ('site-packages', '__pycache__', 'node_modules', '.pytest_cache'):
            return 'environment_or_cache'
    if 'models' in parts:
        return 'models'
    if '存档' in parts or 'tmp' in parts:
        return 'archive_or_tmp'
    if '协作任务' in parts or name == '后续任务_先读这里.md':
        return 'handoff'
    return 'other_project_files'


def process_state(pid):
    result = {}
    base = Path('/proc') / str(pid)
    for filename in ('stat', 'io', 'status'):
        try:
            raw = (base / filename).read_text()
            if filename == 'stat':
                fields = raw.rsplit(') ', 1)[1].split()
                result.update(cpu_ticks=int(fields[11])+int(fields[12]), state=fields[0])
            elif filename == 'io':
                result['io'] = {line.split(':', 1)[0]: int(line.split(':', 1)[1]) for line in raw.splitlines()}
            else:
                result['memory_threads'] = {line.split(':', 1)[0]: line.split(':', 1)[1].strip()
                                            for line in raw.splitlines() if line.split(':', 1)[0] in
                                            ('VmRSS', 'Threads', 'voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches')}
        except (OSError, ValueError):
            result[filename + '_unavailable'] = True
    try:
        raw = Path('/proc/stat').read_text().splitlines()[0].split()[1:]
        result['host_cpu_ticks'] = [int(value) for value in raw]
        result['loadavg'] = Path('/proc/loadavg').read_text().strip()
        result['diskstats'] = [line.split() for line in Path('/proc/diskstats').read_text().splitlines()
                               if line.split()[2] == 'nvme0n1']
    except OSError:
        pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='One snapshot, full remaining-file inventory and route metadata')
    args = parser.parse_args()
    process = subprocess.run([BINARY, 'cli', 'config', 'dump-json'], capture_output=True, text=True, timeout=15)
    if process.returncode:
        raise SystemExit('Local Verysync management unavailable; no configuration printed.')
    config = json.loads(process.stdout)
    gui = config.get('gui', {})
    address = gui.get('address', '127.0.0.1:8886')
    if address.startswith(':'):
        address = '127.0.0.1' + address
    host, port = address.rsplit(':', 1)
    if host in ('0.0.0.0', '::', '[::]'):
        host = '127.0.0.1'
    if not ipaddress.ip_address(host.strip('[]')).is_loopback:
        raise SystemExit('Only loopback management allowed.')
    base = ('https' if gui.get('useTLS') else 'http') + '://' + host + ':' + port
    secret = gui.get('apiKey', gui.get('apikey', ''))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def api(path, query=None):
        if query:
            path += '?' + urllib.parse.urlencode(query)
        try:
            request = urllib.request.Request(base+path, headers={'X-API-Key': secret} if secret else {})
            with opener.open(request, timeout=6) as response:
                return json.load(response)
        except Exception as error:
            return {'api_error': type(error).__name__}

    names = {row.get('deviceID', row.get('deviceId')): row.get('name', '') for row in rows(config.get('devices', []))}
    folders = [row for row in rows(config.get('folders', [])) if Path(row.get('path', '')) == ROOT]
    running = subprocess.run(['pgrep', '-x', 'verysync'], capture_output=True, text=True)
    pids = [int(value) for value in running.stdout.split()]
    report = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'read_only': True,
              'options': select(config.get('options', {}), ('maxSendKbps', 'maxRecvKbps', 'limitBandwidthInLan',
                  'maxFolderConcurrency', 'setLowPriority', 'databaseTuning', 'maxConcurrentIncomingRequestKiB')),
              'devices': [{**select(row, ('name', 'paused', 'compression', 'maxSendKbps', 'maxRecvKbps')),
                           'alias': alias(row.get('deviceID', row.get('deviceId')))}
                          for row in rows(config.get('devices', []))],
              'folders': [], 'samples': []}
    for folder in folders:
        identity = folder.get('id', folder.get('ID'))
        members = [row.get('deviceID', row.get('deviceId')) for row in rows(folder.get('devices', [])) if isinstance(row, dict)]
        item = {**select(folder, ('label', 'path', 'type', 'paused', 'rescanIntervalS', 'fsWatcherEnabled',
                    'fsWatcherDelayS', 'hashers', 'copiers', 'pullers', 'pullerPauseS', 'maxConcurrentWrites',
                    'scanProgressIntervalS', 'order', 'disableFsync', 'maxConflicts', 'minDiskFree')),
                'alias': alias(identity), 'members': [names.get(peer, alias(peer)) for peer in members]}
        ignores = api('/rest/db/ignores', {'folder': identity})
        patterns = ignores.get('ignore') or []
        item['ignores'] = {'count': len(patterns),
                           'environment_cache_related_rules': [rule for rule in patterns if any(
                               term in rule for term in ('venv', '__pycache__', 'node_modules', 'site-packages', 'pytest'))]}
        need = api('/rest/db/need', {'folder': identity, 'page': 1, 'perpage': 10000 if args.quick else 250})
        entries = [{**select(row, ('name', 'type', 'size', 'deleted')), 'group': group,
                    'category': category(row.get('name', ''))}
                   for group in ('progress', 'queued', 'rest') for row in need.get(group) or []]
        item['local_need_sample'] = {'count': len(entries), 'api_error': need.get('api_error'),
                                      'category_counts': dict(Counter(row['category'] for row in entries)),
                                      'top_directory_counts': dict(Counter(row.get('name', '').split('/')[0] for row in entries)),
                                      'top_directory_full_file_bytes': {directory: sum(row.get('size', 0) for row in entries
                                          if row.get('name', '').split('/')[0] == directory)
                                          for directory in set(row.get('name', '').split('/')[0] for row in entries)},
                                      'sample_bytes': sum(row.get('size', 0) for row in entries),
                                      'largest': sorted(entries, key=lambda row: row.get('size', 0), reverse=True)[:12],
                                      'first': entries[:15]}
        errors = api('/rest/folder/errors', {'folder': identity})
        item['errors'] = {'api_error': errors.get('api_error'),
                           'items': [select(row, ('path', 'error')) for row in (errors.get('errors') or [])[:12]]}
        report['folders'].append(item)
        if args.quick and entries:
            item['same_model_path_comparisons'] = []
            for suffix in ('aura/models/tts/OmniVoice/model.safetensors',
                           'aura/models/tts/OmniVoice/audio_tokenizer/model.safetensors',
                           'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx'):
                comparison = {'suffix': suffix, 'files': {}}
                for prefix in ('共享文件夹', '语音共享文件'):
                    info = api('/rest/db/file', {'folder': identity, 'file': prefix+'/'+suffix})
                    value = info.get('global') or {}
                    comparison['files'][prefix] = {'size': value.get('size'),
                        'block_hash_available': bool(value.get('blocksHash') or value.get('blocks')),
                        'block_hash': value.get('blocksHash') or (hashlib.sha256(json.dumps(value['blocks'], sort_keys=True).encode()).hexdigest()
                                                                if value.get('blocks') else None)}
                values = list(comparison['files'].values())
                comparison['same_size'] = values[0]['size'] is not None and values[0]['size'] == values[1]['size']
                comparison['same_block_hash'] = (values[0]['block_hash'] == values[1]['block_hash']
                                                  if all(row['block_hash_available'] for row in values) else None)
                item['same_model_path_comparisons'].append(comparison)
    for sample_index in range(1 if args.quick else 3):
        if sample_index:
            time.sleep(10)
        sample = {'utc': datetime.now(timezone.utc).isoformat(), 'monotonic': time.monotonic(),
                  'processes': {str(pid): process_state(pid) for pid in pids},
                  'system': select(api('/rest/system/status'), ('cpuPercent', 'alloc', 'sys', 'goroutines', 'uptime')),
                  'connections': [], 'folders': []}
        connections = api('/rest/system/connections').get('connections', {})
        for peer, connection in connections.items():
            detail = {'alias': alias(peer), 'name': names.get(peer, ''),
                                           **select(connection, ('connected', 'paused', 'type', 'isLocal', 'inBytesTotal',
                                               'outBytesTotal', 'startedAt', 'clientVersion', 'crypto', 'transport'))}
            if args.quick:
                try:
                    remote = connection.get('address', '').rsplit(':', 1)[0].strip('[]')
                    detail['remote_address_is_private'] = ipaddress.ip_address(remote).is_private
                    route = subprocess.run(['ip', '-j', 'route', 'get', remote], capture_output=True, text=True, timeout=3)
                    if route.returncode == 0:
                        detail['route'] = [select(value, ('dev', 'prefsrc')) for value in json.loads(route.stdout)]
                except (ValueError, OSError, subprocess.TimeoutExpired):
                    detail['route_unavailable'] = True
            sample['connections'].append(detail)
        for folder in folders:
            identity = folder.get('id', folder.get('ID'))
            status = api('/rest/db/status', {'folder': identity})
            members = [row.get('deviceID', row.get('deviceId')) for row in rows(folder.get('devices', [])) if isinstance(row, dict)]
            peers = []
            for peer in members:
                if peer not in connections:
                    continue
                completion = api('/rest/db/completion', {'folder': identity, 'device': peer})
                peers.append({'name': names.get(peer, ''), **select(completion, ('completion', 'needBytes', 'needItems', 'needDeletes', 'remoteState'))})
            sample['folders'].append({'alias': alias(identity), 'peers': peers,
                                      **select(status, ('state', 'stateChanged', 'globalFiles', 'localFiles', 'globalDirectories',
                                          'globalBytes', 'localBytes', 'needFiles', 'needDirectories', 'needDeletes',
                                          'needTotalItems', 'needBytes', 'errors', 'pullErrors', 'api_error'))})
        report['samples'].append(sample)
        if sample_index == 0:
            print(json.dumps({'first_sample': sample, 'configuration': {key: report[key] for key in ('options', 'folders')}}, ensure_ascii=False), flush=True)
    start, end = report['samples'][0], report['samples'][-1]
    elapsed = end['monotonic'] - start['monotonic']
    rates = []
    for connection in end['connections']:
        old = next((row for row in start['connections'] if row['alias'] == connection['alias']), None)
        if elapsed > 0 and old and connection.get('startedAt') == old.get('startedAt'):
            rates.append({'name': connection['name'], 'seconds': round(elapsed, 2),
                           'receive_bytes_per_second': round((connection.get('inBytesTotal', 0)-old.get('inBytesTotal', 0))/elapsed, 1),
                           'send_bytes_per_second': round((connection.get('outBytesTotal', 0)-old.get('outBytesTotal', 0))/elapsed, 1)})
    report['rates'] = rates
    target = WORK / ('speed-diagnosis-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.json')
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'saved': str(target), 'rates': rates, 'final_sample': end}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
