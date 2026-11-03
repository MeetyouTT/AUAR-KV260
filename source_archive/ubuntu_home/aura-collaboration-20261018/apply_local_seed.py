"""Fill only absent voice mirror files whose actual content matches the remote block hash."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
from sync_api import API, alias, utc

ROOT = Path('/home/ghmd/Win共享文件')
WORK = Path(__file__).resolve().parent
BINARY = '/home/ghmd/.local/opt/verysync/verysync'


def set_paused(identity, value):
    process = subprocess.run([BINARY, 'cli', 'config', 'folders', identity, 'paused', 'set',
                              'true' if value else 'false'], capture_output=True, text=True, timeout=20)
    if process.returncode:
        raise RuntimeError('Could not set folder pause state: ' + alias(identity))


def block_size(size, count):
    if size == 0 and count == 0:
        return 1
    if count == 1:
        return max(size, 1)
    sizes = [2**power for power in range(17, 25) if (size + 2**power - 1)//2**power == count]
    if len(sizes) != 1:
        raise ValueError('Ambiguous block layout')
    return sizes[0]


def content_hash(path, length):
    value, entire, count = hashlib.sha256(), hashlib.sha256(), 0
    with path.open('rb') as stream:
        while True:
            data = stream.read(length)
            if not data:
                break
            count += 1
            value.update(hashlib.sha256(data).digest())
            entire.update(data)
    return base64.b64encode(value.digest()).decode(), entire.hexdigest(), count


def remote_mtime_ns(value):
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})', value)
    if not match:
        raise ValueError('Unsupported remote timestamp')
    zone = '+00:00' if match[3] == 'Z' else match[3]
    seconds = int(datetime.fromisoformat(match[1]+zone).timestamp())
    return seconds*1000000000 + int((match[2] or '').ljust(9, '0')[:9])


def safe_path(relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Invalid relative path')
    path = ROOT/rel
    if ROOT not in path.resolve().parents:
        raise ValueError('Path leaves shared root')
    current = ROOT
    for component in rel.parts:
        current = current/component
        if current.is_symlink():
            raise ValueError('Refuse symlink')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    api = API()
    folders = api.folders()
    if args.controls:
        identity = api.identity(folders[0])
        for suffix in (['paused', '--help'], ['paused', 'set', '--help']):
            result = subprocess.run([BINARY, 'cli', 'config', 'folders', identity, *suffix],
                                    capture_output=True, text=True, timeout=15)
            print((result.stdout+result.stderr).replace(identity, alias(identity)))
        return
    if not args.apply:
        raise SystemExit('Choose --controls or --apply')
    plan = json.loads((WORK/'local-seed-plan.json').read_text())
    report = {'started_utc': utc(), 'created': [], 'skipped': [], 'failures': [], 'pause_restored': []}
    target_folder = next(row for row in folders if alias(api.identity(row)) == plan['folder_alias'])
    identity = api.identity(target_folder)
    reusable = [row for row in plan['files'] if row['action'] == 'LOCAL_CONTENT_REUSE']
    def preflight(row):
        remote = api.call('/rest/db/file', {'folder': identity, 'file': row['target']}).get('global') or {}
        valid = (remote.get('blocksHash') == row['blocks_hash'] and remote.get('version') == row['target_version']
                 and not remote.get('deleted') and not remote.get('invalid'))
        return row['target'], valid
    with ThreadPoolExecutor(max_workers=8) as pool:
        preflight_valid = dict(pool.map(preflight, reusable))
    print(json.dumps({'preflight_current_versions': sum(preflight_valid.values()), 'candidates': len(reusable)}), flush=True)
    originals = {api.identity(row): bool(row.get('paused')) for row in folders}
    stamp = str(time.time_ns())
    private = WORK/('pause-state-before-seed-'+stamp+'.json')
    with private.open('x', encoding='utf-8') as stream:
        json.dump({alias(key): value for key, value in originals.items()}, stream)
    paused = []
    try:
        for folder_id, was_paused in originals.items():
            if not was_paused:
                set_paused(folder_id, True)
                paused.append(folder_id)
        time.sleep(2)
        for index, row in enumerate(reusable):
            temporary = None
            try:
                source, destination = safe_path(row['source']), safe_path(row['target'])
                if not row['target'].startswith('语音共享文件/'):
                    raise ValueError('Unexpected target scope')
                if destination.exists() or destination.is_symlink():
                    report['skipped'].append({'target': row['target'], 'reason': 'already_exists'})
                    continue
                before = source.stat()
                if not stat.S_ISREG(before.st_mode) or before.st_size != row['bytes']:
                    raise ValueError('Source size changed')
                if not preflight_valid[row['target']]:
                    report['skipped'].append({'target': row['target'], 'reason': 'remote_version_changed'})
                    continue
                ns = remote_mtime_ns(row['modified'])
                length = block_size(row['bytes'], row['num_blocks'])
                descriptor, name = tempfile.mkstemp(prefix='seed-', dir=WORK)
                temporary = Path(name)
                blocks, entire, count, total = hashlib.sha256(), hashlib.sha256(), 0, 0
                with source.open('rb') as incoming, os.fdopen(descriptor, 'wb') as outgoing:
                    while True:
                        data = incoming.read(length)
                        if not data:
                            break
                        total += len(data)
                        count += 1
                        blocks.update(hashlib.sha256(data).digest())
                        entire.update(data)
                        outgoing.write(data)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if (base64.b64encode(blocks.digest()).decode() != row['blocks_hash']
                        or total != row['bytes'] or count != row['num_blocks']):
                    raise ValueError('Actual source content differs from remote expected blocks')
                after = source.stat()
                if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                    raise ValueError('Source changed during copy')
                os.utime(temporary, ns=(ns, ns))
                os.chmod(temporary, int(row.get('permissions') or '0644', 8) & 0o777)
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.link(temporary, destination)
                copied_blocks, copied_sha, copied_count = content_hash(destination, length)
                if copied_blocks != row['blocks_hash'] or copied_sha != entire.hexdigest() or copied_count != count:
                    raise RuntimeError('Copied content verification failed')
                report['created'].append({'path': row['target'], 'source': row['source'], 'bytes': total,
                                          'sha256': copied_sha, 'expected_blocks_hash_verified': True})
            except Exception as error:
                report['failures'].append({'target': row['target'], 'error': type(error).__name__+': '+str(error)})
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
            if (index+1) % 100 == 0:
                print(json.dumps({'processed': index+1, 'created': len(report['created']),
                                  'created_bytes': sum(item['bytes'] for item in report['created']),
                                  'failures': len(report['failures'])}), flush=True)
    finally:
        for folder_id in reversed(paused):
            try:
                set_paused(folder_id, False)
                report['pause_restored'].append(alias(folder_id))
            except Exception as error:
                report['failures'].append({'folder_alias': alias(folder_id), 'error': str(error)})
        report['finished_utc'] = utc()
        report['created_count'] = len(report['created'])
        report['created_bytes'] = sum(item['bytes'] for item in report['created'])
        (WORK/('local-seed-attempt-'+stamp+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        (WORK/'local-seed-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    summary = {key: value for key, value in report.items() if key not in ('created', 'skipped', 'failures')}
    summary.update(skipped_count=len(report['skipped']), failures=report['failures'][:10])
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
