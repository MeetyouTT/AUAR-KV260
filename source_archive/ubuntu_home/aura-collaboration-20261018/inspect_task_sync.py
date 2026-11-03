"""Inspect this handoff's exact files using the local Verysync API, without secrets."""
import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

ROOT = Path('/home/ghmd/Win共享文件')
TASK = '协作任务/2026-10-18_双机联调'
FILES = ['后续任务_先读这里.md'] + [TASK + '/' + name for name in (
    '任务总表.md', 'Windows_执行回执.md', 'Ubuntu_执行回执.md', '当前进度与证据.md',
    '参考资料/2026-10-18-BOARD-ETHERNET-PEER.md',
    '参考资料/2026-10-12-MULTI-MODEL-SCHEDULER-FIRST-MILESTONE.md',
    'evidence/ubuntu/board-network-20261018.output')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan', action='store_true', help='Rescan only the handoff files')
    args = parser.parse_args()
    process = subprocess.run(
        ['/home/ghmd/.local/opt/verysync/verysync', 'cli', 'config', 'dump-json'],
        capture_output=True, text=True, timeout=15)
    if process.returncode:
        raise SystemExit('Local Verysync configuration API unavailable; no secrets printed.')
    config = json.loads(process.stdout)
    gui = config.get('gui', {})
    address = gui.get('address', '127.0.0.1:8886')
    if address.startswith(':'):
        address = '127.0.0.1' + address
    host, port = address.rsplit(':', 1)
    if host in ('0.0.0.0', '::', '[::]'):
        host = '127.0.0.1'
    if not ipaddress.ip_address(host.strip('[]')).is_loopback:
        raise SystemExit('Only the loopback management API is allowed.')
    base = ('https' if gui.get('useTLS') else 'http') + '://' + host + ':' + port
    secret = gui.get('apiKey', gui.get('apikey', ''))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def api(path, query=None, post=False):
        if query:
            path += '?' + urllib.parse.urlencode(query)
        request = urllib.request.Request(base + path, data=b'' if post else None,
                                         headers={'X-API-Key': secret} if secret else {})
        try:
            with opener.open(request, timeout=15) as response:
                raw = response.read()
                return json.loads(raw) if raw else {'ok': True}
        except Exception as error:
            return {'api_error': type(error).__name__}

    def rows(value):
        return value if isinstance(value, list) else list(value.values()) if isinstance(value, dict) else []

    def alias(value):
        return hashlib.sha256(str(value).encode()).hexdigest()[:10]

    names = {row.get('deviceID', row.get('deviceId')): row.get('name', '')
             for row in rows(config.get('devices', []))}
    connections = api('/rest/system/connections').get('connections', {})
    observed = datetime.now(timezone.utc)
    report = {'observed_utc': observed.isoformat(), 'task_version': 'AURA-COLLAB-20261018-r1',
              'scope': 'SYNC_INDEX_ONLY_NOT_WINDOWS_DISK_OR_BUSINESS_ACCEPTANCE',
              'windows_receipt_is_initial_template': '尚不代表 Windows 已接收或执行' in
                  (ROOT / TASK / 'Windows_执行回执.md').read_text(encoding='utf-8'),
              'folders': []}
    for folder in rows(config.get('folders', [])):
        if Path(folder.get('path', '')) != ROOT:
            continue
        identity = folder.get('id', folder.get('ID'))
        members = [row.get('deviceID', row.get('deviceId'))
                   for row in rows(folder.get('devices', [])) if isinstance(row, dict)]
        peers = [peer for peer in members if peer in connections]
        result = {'folder_alias': alias(identity), 'path': str(ROOT),
                  'type': folder.get('type'), 'paused': folder.get('paused'), 'peers': [], 'files': []}
        if args.scan:
            result['targeted_scans'] = [api('/rest/db/scan', {'folder': identity, 'sub': relative}, post=True)
                                       for relative in ('后续任务_先读这里.md', TASK)]
        status = api('/rest/db/status', {'folder': identity})
        result['status'] = {key: status.get(key) for key in
                            ('state', 'needTotalItems', 'needBytes', 'errors', 'pullErrors', 'api_error')}
        for peer in peers:
            completion = api('/rest/db/completion', {'folder': identity, 'device': peer})
            connection = connections[peer]
            result['peers'].append({'alias': alias(peer), 'name': names.get(peer, ''),
                                    'connected': connection.get('connected'), 'type': connection.get('type'),
                                    'isLocal': connection.get('isLocal'),
                                    **{key: completion.get(key) for key in
                                       ('completion', 'needItems', 'needBytes', 'remoteState', 'api_error')}})
        for relative in FILES:
            content = (ROOT / relative).read_bytes()
            info = api('/rest/db/file', {'folder': identity, 'file': relative})
            global_file, local = info.get('global') or {}, info.get('local') or {}
            available = [row.get('id', row.get('deviceID')) for row in info.get('availability') or []
                         if isinstance(row, dict) and not row.get('fromTemporary')]
            current = (local.get('size') == global_file.get('size') == len(content)
                       and local.get('version') == global_file.get('version')
                       and not any(row.get(flag) for row in (global_file, local)
                                   for flag in ('deleted', 'invalid', 'ignored')))
            result['files'].append({'path': relative, 'bytes': len(content),
                                    'sha256': hashlib.sha256(content).hexdigest(),
                                    'local_matches_current_global_index': current,
                                    'available_on': [names.get(peer, alias(peer)) for peer in peers
                                                     if peer in available and current],
                                    'api_error': info.get('api_error')})
        for peer in result['peers']:
            peer['all_handoff_files_index_confirmed'] = all(
                peer['name'] in row['available_on'] for row in result['files'])
        report['folders'].append(result)
    if not report['folders']:
        raise SystemExit('No configured sync folder matches the authorized shared root.')
    stamp = observed.strftime('%Y%m%dT%H%M%S.%fZ')
    target = Path(__file__).resolve().parent / ('task-sync-' + stamp + '.json')
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'saved': str(target), 'observed_utc': report['observed_utc'],
                      'folders': [{key: value for key, value in row.items() if key != 'files'}
                                  for row in report['folders']]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
