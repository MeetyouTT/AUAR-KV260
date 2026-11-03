#!/usr/bin/env python3
"""Read selected files from the local baseline image without mounting it.

This deliberately small ext4 reader supports the extents used by this image.
All disk access uses rb. It cannot write the image or access board devices.
Unsupported formats raise an error rather than fabricate an inventory.
"""
import hashlib
import json
from pathlib import Path
import struct
import uuid

ROOT = Path(__file__).resolve().parent
IMAGE = Path('/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img')

class Ext4:
    def __init__(self, path, offset):
        self.f = path.open('rb')
        self.offset = offset
        sb = self.read(1024, 1024)
        assert struct.unpack_from('<H', sb, 56)[0] == 0xef53
        self.block_size = 1024 << struct.unpack_from('<I', sb, 24)[0]
        self.inodes_per_group = struct.unpack_from('<I', sb, 40)[0]
        self.inode_size = struct.unpack_from('<H', sb, 88)[0]
        self.desc_size = max(32, struct.unpack_from('<H', sb, 254)[0])
        self.gdt = (2 if self.block_size == 1024 else 1) * self.block_size
        self.uuid = str(uuid.UUID(bytes=sb[104:120]))
        self.label = sb[120:136].split(b'\0')[0].decode()

    def read(self, start, count):
        if start < 0 or count < 0:
            raise ValueError('Invalid offset')
        self.f.seek(self.offset + start)
        data = self.f.read(count)
        if len(data) != count:
            raise ValueError('Short image read')
        return data

    def inode(self, number):
        group, index = divmod(number - 1, self.inodes_per_group)
        gd = self.read(self.gdt + group * self.desc_size, self.desc_size)
        table = struct.unpack_from('<I', gd, 8)[0]
        if self.desc_size >= 64:
            table |= struct.unpack_from('<I', gd, 40)[0] << 32
        return self.read(table * self.block_size + index * self.inode_size, self.inode_size)

    def extents(self, header):
        magic, count, maximum, depth, gen = struct.unpack_from('<HHHHI', header)
        if magic != 0xf30a or count > maximum or depth > 5:
            raise ValueError('Unsupported extent metadata')
        for index in range(count):
            pos = 12 + index * 12
            logical = struct.unpack_from('<I', header, pos)[0]
            if depth:
                low, high = struct.unpack_from('<IH', header, pos + 4)
                yield from self.extents(self.read((low | high << 32) * self.block_size, self.block_size))
            else:
                length, high, low = struct.unpack_from('<HHI', header, pos + 4)
                uninitialized = length > 32768
                length = length - 32768 if uninitialized else length
                yield logical, length, (low | high << 32), uninitialized

    def data(self, number):
        ino = self.inode(number)
        mode = struct.unpack_from('<H', ino, 0)[0]
        size = struct.unpack_from('<I', ino, 4)[0] | struct.unpack_from('<I', ino, 108)[0] << 32
        flags = struct.unpack_from('<I', ino, 32)[0]
        if size > 128 * 1024 * 1024:
            raise ValueError('File exceeds audit memory limit')
        if mode & 0xf000 == 0xa000 and size <= 60:
            return ino[40:40 + size]
        if not flags & 0x80000:
            raise ValueError('Non-extent inode is unsupported')
        out = bytearray(size)
        for logical, length, physical, uninitialized in self.extents(ino[40:100]):
            begin = logical * self.block_size
            count = min(length * self.block_size, size - begin)
            if count > 0 and not uninitialized:
                out[begin:begin + count] = self.read(physical * self.block_size, count)
        return bytes(out)

    def directory(self, number):
        data = self.data(number)
        pos = 0
        while pos + 8 <= len(data):
            ino, reclen, namelen, kind = struct.unpack_from('<IHBB', data, pos)
            if reclen < 8 or namelen > reclen - 8:
                raise ValueError('Invalid directory entry')
            if ino:
                yield data[pos + 8:pos + 8 + namelen].decode('utf-8', 'replace'), ino, kind
            pos += reclen

    def lookup(self, path, links=0):
        if links > 20:
            raise ValueError('Symlink loop')
        parts = [p for p in path.split('/') if p]
        current = 2
        prefix = []
        for index, part in enumerate(parts):
            found = next(((ino, kind) for name, ino, kind in self.directory(current) if name == part), None)
            if found is None:
                raise FileNotFoundError(path)
            current, kind = found
            if kind == 7:
                target = self.data(current).decode()
                base = '' if target.startswith('/') else '/' + '/'.join(prefix) + '/'
                new_path = base + target + '/' + '/'.join(parts[index + 1:])
                return self.lookup(new_path, links + 1)
            prefix.append(part)
        return current

def main():
    meta = json.loads((ROOT / 'host-image-partitions.json').read_text())
    fs = Ext4(IMAGE, meta['partitions'][1]['offset'])
    paths = ['/etc/os-release', '/etc/vart.conf', '/etc/fstab', '/etc/init.d/dpu-auto-config',
             '/home/root/dpu_sw_optimize/zynqmp/zynqmp_dpu_optimize.sh',
             '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin',
             '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo',
             '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin',
             '/lib/firmware/xilinx/kv260-benchmark-b4096/shell.json']
    rows = []
    for path in paths:
        row = {'path_in_local_image': path}
        try:
            data = fs.data(fs.lookup(path))
            row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            if path.endswith(('.conf', '.json', '.sh')) or path in paths[:4]:
                row['text'] = data.decode('utf-8', 'replace')
        except Exception as exc:
            row['error'] = repr(exc)
        rows.append(row)
    (ROOT / 'host-image-root-files.json').write_text(json.dumps({
        'source': str(IMAGE), 'method': 'Read ext4 inode/extents via rb; no mount or loop device',
        'filesystem_uuid': fs.uuid, 'filesystem_label': fs.label, 'files': rows
    }, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(rows, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
