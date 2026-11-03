"""Reuse existing identical files locally; create absent destinations without overwriting."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import tempfile


def mtime_ns(value):
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})', value)
    if not match:
        raise ValueError('Unsupported timestamp')
    zone = '+00:00' if match[3] == 'Z' else match[3]
    return int(datetime.fromisoformat(match[1]+zone).timestamp())*1000000000 + int((match[2] or '').ljust(9, '0')[:9])


def block_size(size, count):
    if count <= 1:
        return max(size, 1)
    values = [2**power for power in range(17, 25) if (size+2**power-1)//2**power == count]
    if len(values) != 1:
        raise ValueError('Ambiguous content block layout')
    return values[0]


def safe_path(root, relative):
    value = Path(relative)
    if value.is_absolute() or '..' in value.parts:
        raise ValueError('Invalid relative path')
    target = root/value
    if root not in target.resolve().parents:
        raise ValueError('Path leaves sync root')
    current = root
    for component in value.parts:
        current = current/component
        if current.is_symlink():
            raise ValueError('Symlink path refused')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sync-root', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Create only absent, verified files; default is preview')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--report-dir', type=Path)
    args = parser.parse_args()
    root = args.sync_root.resolve(strict=True)
    base = Path(__file__).resolve().parent
    manifest = json.loads((args.manifest or base/'重复文件本地补齐清单.json').read_text(encoding='utf-8'))
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'apply': args.apply,
              'platform': platform.system(), 'sync_root': str(root),
              'created': [], 'skipped': [], 'failed': []}
    for row in manifest['files']:
        temporary = None
        try:
            source, target = safe_path(root, row['source']), safe_path(root, row['target'])
            if target.exists() or target.is_symlink():
                report['skipped'].append({'path': row['target'], 'reason': 'already_exists'})
                continue
            if not source.is_file() or source.stat().st_size != row['bytes']:
                report['skipped'].append({'path': row['target'], 'reason': 'source_missing_or_size_changed'})
                continue
            if not args.apply:
                report['skipped'].append({'path': row['target'], 'reason': 'preview_candidate', 'bytes': row['bytes']})
                continue
            length = block_size(row['bytes'], row['num_blocks'])
            ns = mtime_ns(row['modified'])
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix='.aura-seed-', suffix='.tmp', dir=str(target.parent))
            temporary = Path(name)
            blocks, entire, total, count = hashlib.sha256(), hashlib.sha256(), 0, 0
            with source.open('rb') as incoming, os.fdopen(descriptor, 'wb') as outgoing:
                while True:
                    data = incoming.read(length)
                    if not data:
                        break
                    blocks.update(hashlib.sha256(data).digest())
                    entire.update(data)
                    total += len(data)
                    count += 1
                    outgoing.write(data)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            if (base64.b64encode(blocks.digest()).decode() != row['blocks_hash']
                    or total != row['bytes'] or count != row['num_blocks']):
                raise ValueError('Source content differs from verified manifest')
            os.utime(temporary, ns=(ns, ns))
            if os.name == 'nt':
                # Windows rename fails if the destination exists. It never replaces it.
                os.rename(str(temporary), str(target))
            else:
                os.link(str(temporary), str(target))
            copied = hashlib.sha256()
            with target.open('rb') as stream:
                for data in iter(lambda: stream.read(4*1024*1024), b''):
                    copied.update(data)
            if copied.hexdigest() != entire.hexdigest():
                raise RuntimeError('Destination SHA256 verification failed')
            report['created'].append({'path': row['target'], 'bytes': total, 'sha256': copied.hexdigest()})
            print('CREATED '+row['target'], flush=True)
        except FileExistsError:
            report['skipped'].append({'path': row['target'], 'reason': 'destination_arrived_during_copy'})
        except Exception as error:
            report['failed'].append({'path': row['target'], 'error': type(error).__name__+': '+str(error)})
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['created_count'] = len(report['created'])
    report['created_bytes'] = sum(row['bytes'] for row in report['created'])
    destination = (args.report_dir or base)/('本地补齐结果_'+platform.system()+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.json')
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'report': str(destination), 'apply': args.apply,
                      'created_count': report['created_count'], 'created_bytes': report['created_bytes'],
                      'skipped_count': len(report['skipped']), 'failures': len(report['failed'])}, ensure_ascii=False))
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
