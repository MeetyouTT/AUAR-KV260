#!/usr/bin/env python3
"""Inspect filesystem copies taken from the already-verified whole-card image."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

ROOT = Path('/home/ghmd/kv260-sd-backup-20261003')
IMAGE = ROOT / 'kv260-spare-runtime-fixed-20261003.img'
OUT = ROOT / 'offline-inspection'
CHUNK = 1024 * 1024

def emit(event, **values):
    print(json.dumps({'event': event, **values}), flush=True)

def run(name, argv):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (OUT / (name + '.stdout')).write_bytes(result.stdout)
    (OUT / (name + '.stderr')).write_bytes(result.stderr)
    (OUT / (name + '.rc')).write_text(str(result.returncode) + '\n')
    emit('command_finished', name=name, return_code=result.returncode)
    return result.returncode

def extract(start, size, target):
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with IMAGE.open('rb') as source, os.fdopen(fd, 'wb') as dest:
        source.seek(start)
        left = size
        while left:
            data = source.read(min(CHUNK, left))
            if not data:
                raise RuntimeError('unexpected end of verified image')
            if data == b'\0' * len(data):
                dest.seek(len(data), 1)
            else:
                dest.write(data)
            left -= len(data)
        dest.truncate(size)
        dest.flush()
        os.fsync(dest.fileno())
    emit('partition_copy_ready', path=str(target), bytes=size,
         allocated_bytes=target.stat().st_blocks * 512)

def main():
    verification = json.loads((ROOT / 'IMAGE_VERIFICATION.json').read_text())
    if not verification['verified'] or IMAGE.stat().st_size != verification['source_bytes']:
        raise RuntimeError('whole-card image is not accepted')
    OUT.mkdir(mode=0o700)
    with IMAGE.open('rb') as stream:
        header = stream.read(512)
    if '%08x' % struct.unpack_from('<I', header, 440)[0] != '40bd38f0':
        raise RuntimeError('unexpected MBR identity')
    parts = []
    for i in (0, 1):
        entry = header[446+16*i:462+16*i]
        start, size = struct.unpack_from('<II', entry, 8)
        parts.append({'index': i+1, 'type': entry[4],
                      'offset_bytes': start*512, 'bytes': size*512})
    if parts != [
        {'index': 1, 'type': 12, 'offset_bytes': 4096, 'bytes': 79150080},
        {'index': 2, 'type': 131, 'offset_bytes': 79155200, 'bytes': 31835828224}]:
        raise RuntimeError('partition layout differs from source preflight')
    (OUT / 'partitions.json').write_text(json.dumps(parts, indent=2) + '\n')
    for part, name in zip(parts, ('boot.original.fat', 'root.original.ext4')):
        extract(part['offset_bytes'], part['bytes'], OUT / name)
    statuses = {}
    statuses['fat_readonly_check'] = run('fat-readonly-check', ['fsck.fat', '-n', '-v', str(OUT / 'boot.original.fat')])
    statuses['root_readonly_check'] = run('root-readonly-check', ['e2fsck', '-f', '-n', str(OUT / 'root.original.ext4')])
    statuses['fstab_dump'] = run('fstab-dump', ['debugfs', '-R', 'dump /etc/fstab '+str(OUT/'fstab.original'), str(OUT/'root.original.ext4')])
    checks = {}
    archive_specs = {
        'postboot-soak.tar.gz': 'ed85e8e88773df6a3c14428dc4c7c1aa4cd5bbf7f4b9b7a51bea31601cee6700',
        'postboot-soak-kernel.tar.gz': 'ed980300c2191ce3a03cbf3b729eb94c6abd7ef2a4635af361523972c11ce77c',
    }
    for name, expected in archive_specs.items():
        source = '/home/root/kv260-runtime-persistent-backup-20261003/' + name
        target = OUT / name
        statuses[name+'_dump'] = run(name+'-dump', ['debugfs', '-R', 'dump '+source+' '+str(target), str(OUT/'root.original.ext4')])
        actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        checks[name] = {'expected_sha256': expected, 'actual_sha256': actual, 'matches': actual == expected}
    report = {'commands': statuses, 'board_soak_archive_checks': checks,
              'all_board_soak_archives_match': all(item['matches'] for item in checks.values()),
              'scope': 'read-only checks on partition copies; original SD and full-card image not modified'}
    (OUT/'INSPECTION.json').write_text(json.dumps(report, indent=2) + '\n')
    emit('inspection_finished', **report)

if __name__ == '__main__':
    main()
