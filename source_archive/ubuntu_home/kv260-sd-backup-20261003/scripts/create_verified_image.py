#!/usr/bin/env python3
"""Use UDisks' authenticated read-only interface to image the identified spare SD."""
import array
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import sys
import time

from gi.repository import Gio, GLib

ROOT = Path('/home/ghmd/kv260-sd-backup-20261003')
SOURCE = Path('/dev/disk/by-id/usb-Mass_Storage_Device_121220160204-0:0')
DEVICE = Path('/dev/sda')
SIZE = 31914983424
EXPECTED_TABLE_ID = '40bd38f0'
OBJECT = '/org/freedesktop/UDisks2/block_devices/sda'
IMAGE = ROOT / 'kv260-spare-runtime-fixed-20261003.img'
PARTIAL = IMAGE.with_suffix('.img.partial')
CHUNK = 8 * 1024 * 1024
BUS = 'org.freedesktop.UDisks2'

def emit(event, **values):
    item = {'event': event, 'host_epoch': time.time(), **values}
    line = json.dumps(item, ensure_ascii=False)
    print(line, flush=True)
    with (ROOT / 'progress.jsonl').open('a') as stream:
        stream.write(line + '\n')

def mounted_source_parts():
    return [line.strip() for line in Path('/proc/self/mountinfo').read_text().splitlines()
            if line.split()[2] in ('8:0', '8:1', '8:2')]

def get_properties(connection, interface):
    result = connection.call_sync(
        BUS, OBJECT, 'org.freedesktop.DBus.Properties', 'GetAll',
        GLib.Variant('(s)', (interface,)), GLib.VariantType.new('(a{sv})'),
        Gio.DBusCallFlags.NONE, 10000, None)
    return result.unpack()[0]

def main():
    if SOURCE.resolve() != DEVICE or not DEVICE.exists():
        raise RuntimeError('identified reader device changed or is absent')
    if mounted_source_parts():
        raise RuntimeError('source card still has mounted partitions')
    if IMAGE.exists() or PARTIAL.exists():
        raise RuntimeError('backup output already exists; refusing to overwrite')
    if shutil.disk_usage(ROOT).free < SIZE + 1024 ** 3:
        raise RuntimeError('insufficient destination free space')
    connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    block = get_properties(connection, 'org.freedesktop.UDisks2.Block')
    device_name = bytes(block['Device']).rstrip(b'\0').decode()
    if device_name != str(DEVICE) or block['Size'] != SIZE or block['HintSystem']:
        raise RuntimeError('device identity, capacity or system-disk guard failed')
    if block['Drive'] != '/org/freedesktop/UDisks2/drives/Mass_Storage_Device_121220160204':
        raise RuntimeError('reader identity changed')
    emit('awaiting_system_authorization', device=str(DEVICE), bytes=SIZE,
         method='UDisks2.Block.OpenForBackup', mode='read only')
    result, descriptors = connection.call_with_unix_fd_list_sync(
        BUS, OBJECT, 'org.freedesktop.UDisks2.Block', 'OpenForBackup',
        GLib.Variant('(a{sv})', ({},)), GLib.VariantType.new('(h)'),
        Gio.DBusCallFlags.NONE, 180000, None, None)
    fd = descriptors.get(result.unpack()[0])
    try:
        info = os.fstat(fd)
        if not stat.S_ISBLK(info.st_mode) or info.st_rdev != os.stat(DEVICE).st_rdev:
            raise RuntimeError('returned descriptor is not the identified block device')
        if fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY:
            raise RuntimeError('backup descriptor is not read only')
        size_buffer = array.array('Q', [0])
        fcntl.ioctl(fd, 0x80081272, size_buffer, True)  # BLKGETSIZE64
        if size_buffer[0] != SIZE:
            raise RuntimeError('open descriptor size changed')
        header = os.pread(fd, 512, 0)
        if header[510:512] != b'\x55\xaa' or '%08x' % struct.unpack_from('<I', header, 440)[0] != EXPECTED_TABLE_ID:
            raise RuntimeError('MBR identity differs from preflight')
        if mounted_source_parts():
            raise RuntimeError('a source partition was mounted after authorization')
        emit('copy_started', source=str(SOURCE), output=str(PARTIAL), bytes=SIZE)
        source_digest = hashlib.sha256()
        start = last_report = time.monotonic()
        count = 0
        out_fd = os.open(PARTIAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(out_fd, 'wb') as output:
            while count < SIZE:
                data = os.read(fd, min(CHUNK, SIZE - count))
                if not data:
                    raise RuntimeError('unexpected end of source disk')
                source_digest.update(data)
                output.write(data)
                count += len(data)
                now = time.monotonic()
                if now - last_report >= 30 or count == SIZE:
                    emit('copy_progress', bytes_copied=count, total_bytes=SIZE,
                         elapsed_seconds=round(now-start, 2),
                         MiB_per_second=round(count / (now-start) / 1024**2, 2))
                    last_report = now
            output.flush()
            os.fsync(output.fileno())
        if os.read(fd, 1) != b'':
            raise RuntimeError('source disk exceeds expected size')
        if mounted_source_parts():
            raise RuntimeError('source card was remounted during copy')
        emit('image_readback_started', bytes=SIZE, source_sha256=source_digest.hexdigest())
        image_digest = hashlib.sha256()
        with PARTIAL.open('rb') as saved:
            for data in iter(lambda: saved.read(CHUNK), b''):
                image_digest.update(data)
        if PARTIAL.stat().st_size != SIZE or source_digest.digest() != image_digest.digest():
            raise RuntimeError('saved image size or independent readback hash differs')
        PARTIAL.rename(IMAGE)
        result = {
            'source': str(SOURCE), 'resolved_source': str(DEVICE),
            'source_bytes': SIZE, 'image_bytes': IMAGE.stat().st_size,
            'source_sha256_computed_during_copy': source_digest.hexdigest(),
            'image_sha256_from_independent_readback': image_digest.hexdigest(),
            'verified': True, 'image': str(IMAGE), 'image_mode': '0600',
            'elapsed_seconds': round(time.monotonic()-start, 2),
            'source_access': 'UDisks2 OpenForBackup, O_RDONLY confirmed',
            'source_table_id': EXPECTED_TABLE_ID,
            'card_identity_basis': 'capacity, MBR identity, mounted repaired manager/ZOCL hashes; USB reader does not expose SD CID',
        }
        (ROOT / 'IMAGE_VERIFICATION.json').write_text(json.dumps(result, indent=2) + '\n')
        (ROOT / 'IMAGE_SHA256SUMS').write_text(image_digest.hexdigest()+'  '+IMAGE.name+'\n')
        emit('backup_verified', **result)
    finally:
        os.close(fd)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        emit('failed', error=str(exc), exception_type=type(exc).__name__)
        sys.exit(1)
