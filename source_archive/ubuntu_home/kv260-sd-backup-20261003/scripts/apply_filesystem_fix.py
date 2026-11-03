#!/usr/bin/env python3
"""Apply the reviewed FAT flag repair and fstab deduplication to the spare SD."""
import collections
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import subprocess
import sys

ROOT = Path('/home/ghmd/kv260-sd-backup-20261003')
MOUNT = ROOT / 'rootfs-mount'
DEVICE = Path('/dev/sda')
BY_ID = Path('/dev/disk/by-id/usb-Mass_Storage_Device_121220160204-0:0')
STOCK = Path('/home/ghmd/kv260-runtime-persistent-plan-20261003/stage_payload/stock.sha256')
EXPECTED = {
    'fat_original_sha256': '27e40502c706762014ae172bef80f0c516d34bcf6d3180c880b02f268d3dc623',
    'fat_repaired_sha256': '33a10404abf33d181160dfb58b5b8905611eb64ef6f78abd2b52e7019a40f2db',
    'fstab_original_sha256': 'b1978c1e094cd260b761afbaab75f0d9e659a78044d1d4fd86807bc44ef158bd',
    'fstab_reviewed_sha256': '580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0',
}
REPORT = {'completed_stages': [], 'original_card_fat_modified': False,
          'original_card_fstab_modified': False, 'board_reboot_verified': False}

def save():
    (ROOT / 'FILESYSTEM_FIX_RESULT.json').write_text(json.dumps(REPORT, indent=2) + '\n')

def digest(path, limit=None):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        left = limit
        while left is None or left:
            data = stream.read(1024*1024 if left is None else min(left, 1024*1024))
            if not data:
                if left:
                    raise RuntimeError('unexpected end of source')
                break
            h.update(data)
            if left is not None:
                left -= len(data)
    return h.hexdigest()

def mounted_parts():
    return [line for line in Path('/proc/self/mountinfo').read_text().splitlines()
            if line.split()[2] in ('8:0', '8:1', '8:2')]

def run(name, argv, accepted=(0,)):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (ROOT / (name+'.stdout')).write_bytes(result.stdout)
    (ROOT / (name+'.stderr')).write_bytes(result.stderr)
    (ROOT / (name+'.rc')).write_text(str(result.returncode)+'\n')
    print(json.dumps({'stage': name, 'return_code': result.returncode}), flush=True)
    if result.returncode not in accepted:
        raise RuntimeError('%s failed with %d' % (name, result.returncode))
    REPORT['completed_stages'].append(name)
    save()

def rooted(path):
    pending = collections.deque(PurePosixPath(path).parts[1:])
    resolved = []
    links = 0
    while pending:
        piece = pending.popleft()
        if piece in ('', '.'):
            continue
        if piece == '..':
            if resolved:
                resolved.pop()
            continue
        item = MOUNT.joinpath(*resolved, piece)
        if item.is_symlink():
            links += 1
            if links > 40:
                raise RuntimeError('excessive symlinks in source filesystem')
            target = os.readlink(item)
            pieces = PurePosixPath(target).parts
            if target.startswith('/'):
                resolved = []
                pieces = pieces[1:]
            pending.extendleft(reversed(pieces))
        else:
            resolved.append(piece)
    return MOUNT.joinpath(*resolved)

def stock_check(name):
    rows = []
    for line in STOCK.read_text().splitlines():
        expected, path = line.split('  ', 1)
        actual = digest(rooted(path))
        rows.append({'path': path, 'expected': expected, 'actual': actual, 'matches': actual == expected})
    (ROOT/(name+'.json')).write_text(json.dumps(rows, indent=2)+'\n')
    if len(rows) != 26 or not all(row['matches'] for row in rows):
        raise RuntimeError('original 26-file baseline does not match')
    REPORT[name] = '26/26 matched'
    save()

def main():
    if os.geteuid() != 0:
        raise RuntimeError('system administrator authentication required')
    plan = json.loads((ROOT/'FILESYSTEM_REPAIR_PLAN.json').read_text())
    verified = json.loads((ROOT/'IMAGE_VERIFICATION.json').read_text())
    if not verified['verified'] or verified['image_sha256_from_independent_readback'] != '518942a62c0d0ed32b2a90b4736b821b3e24006157ab420d02d5b54d0470546b':
        raise RuntimeError('verified whole-card recovery point missing')
    if any(plan[key] != value for key, value in EXPECTED.items()) or plan['fat_exact_byte_changes'] != [{'offset': 37, 'old': 1, 'new': 0}]:
        raise RuntimeError('reviewed repair plan changed')
    inspection = json.loads((ROOT/'offline-inspection/INSPECTION.json').read_text())
    if inspection['commands']['root_readonly_check'] != 0 or not inspection['all_board_soak_archives_match']:
        raise RuntimeError('source inspection did not pass')
    if BY_ID.resolve() != DEVICE or int(Path('/sys/class/block/sda/size').read_text())*512 != 31914983424 or mounted_parts():
        raise RuntimeError('source identity, size or unmounted guard failed')
    with DEVICE.open('rb') as stream:
        header = stream.read(512)
    if '%08x' % struct.unpack_from('<I',header,440)[0] != '40bd38f0':
        raise RuntimeError('source partition-table identity changed')
    if digest('/dev/sda1', 79150080) != EXPECTED['fat_original_sha256']:
        raise RuntimeError('current boot partition differs from original backup')
    if digest(ROOT/'fstab.reviewed') != EXPECTED['fstab_reviewed_sha256']:
        raise RuntimeError('reviewed fstab changed')
    REPORT['preflight_passed'] = True
    save()

    run('card-fat-repair', ['/usr/sbin/fsck.fat', '-a', '-v', '/dev/sda1'], (0,1))
    REPORT['original_card_fat_modified'] = True
    actual = digest('/dev/sda1',79150080)
    REPORT['card_fat_sha256_after'] = actual
    save()
    if actual != EXPECTED['fat_repaired_sha256']:
        raise RuntimeError('card FAT result differs from reviewed exact one-byte repair')
    run('card-fat-recheck', ['/usr/sbin/fsck.fat', '-n', '-v', '/dev/sda1'])

    MOUNT.mkdir(mode=0o700)
    run('card-root-mount', ['/usr/bin/mount', '-t', 'ext4', '-o', 'rw,nosuid,nodev,noexec', '/dev/sda2', str(MOUNT)])
    try:
        if os.stat(MOUNT).st_dev != os.stat('/dev/sda2').st_rdev:
            raise RuntimeError('mounted root is not the source card partition')
        fstab = MOUNT/'etc/fstab'
        if fstab.is_symlink() or not stat.S_ISREG(fstab.stat().st_mode) or digest(fstab) != EXPECTED['fstab_original_sha256']:
            raise RuntimeError('source fstab differs from reviewed original')
        stock_check('stock-check-before-fstab')
        backup = MOUNT/'etc/fstab.kv260-pre-dedup-20261003'
        temporary = MOUNT/'etc/fstab.kv260-dedup.tmp'
        if backup.exists() or temporary.exists():
            raise RuntimeError('source backup or temporary file already exists')
        original_stat = fstab.stat()
        shutil.copy2(fstab, backup)
        REPORT['card_fstab_backup'] = '/etc/'+backup.name
        fd = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, stat.S_IMODE(original_stat.st_mode))
        with os.fdopen(fd,'wb') as stream:
            stream.write((ROOT/'fstab.reviewed').read_bytes())
            stream.flush()
            os.fchown(stream.fileno(),original_stat.st_uid,original_stat.st_gid)
            os.fsync(stream.fileno())
        temporary.replace(fstab)
        directory_fd = os.open(fstab.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        REPORT['original_card_fstab_modified'] = True
        REPORT['card_fstab_sha256_after'] = digest(fstab)
        save()
        if REPORT['card_fstab_sha256_after'] != EXPECTED['fstab_reviewed_sha256']:
            raise RuntimeError('fstab writeback hash mismatch')
        stock_check('stock-check-after-fstab')
        REPORT['fstab_mount_entries_after'] = [line for line in fstab.read_text().splitlines()
                                               if line.strip() and not line.lstrip().startswith('#') and line.split()[1]=='/boot']
        save()
    finally:
        run('card-root-unmount', ['/usr/bin/umount', str(MOUNT)])
    run('card-root-final-readonly-check', ['/usr/sbin/e2fsck', '-f', '-n', '/dev/sda2'])
    if mounted_parts():
        raise RuntimeError('source partitions remain mounted after repair')
    REPORT['offline_repair_verified'] = True
    save()
    print(json.dumps(REPORT),flush=True)

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        REPORT['error'] = str(exc)
        save()
        print(json.dumps({'error':str(exc),'completed_stages':REPORT['completed_stages']}),flush=True)
        sys.exit(1)
