import gzip
import struct
from pathlib import Path

AUD = Path('/home/ghmd/kv260_readonly_audit_20260927_7sM1wd')
IMG = Path('/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz')
with gzip.open(IMG, 'rb') as f:
    data = f.read((154600 * 512) + 4096)

with (AUD / 'logs/official_image_static.txt').open('w') as out:
    out.write(f'Inspected first {len(data)} uncompressed bytes only.\n')
    fat_start = 8 * 512
    b = data[fat_start:fat_start+512]
    bps = struct.unpack_from('<H', b, 11)[0]
    spc = b[13]
    reserved = struct.unpack_from('<H', b, 14)[0]
    nfats = b[16]
    fatsz16 = struct.unpack_from('<H', b, 22)[0]
    root_entries = struct.unpack_from('<H', b, 17)[0]
    fat_type = b[54:62].decode('ascii', 'replace').strip()
    sectors = struct.unpack_from('<I', b, 32)[0]
    out.write(f'FAT boot signature={b[510:512].hex()} type_label={fat_type} bytes_per_sector={bps} sectors_per_cluster={spc} reserved={reserved} nfats={nfats} fat_sectors16={fatsz16} root_entries={root_entries} total_sectors={sectors}\n')
    if bps == 512 and fat_type == 'FAT16':
        root_offset = fat_start + (reserved + nfats * fatsz16) * bps
        out.write(f'FAT16 root directory at byte offset={root_offset}\n')
        raw = data[root_offset:root_offset+root_entries*32]
        for pos in range(0, len(raw), 32):
            e = raw[pos:pos+32]
            if not e or e[0] == 0:
                break
            if e[0] == 0xe5 or e[11] == 0x0f:
                continue
            name = e[0:8].decode('ascii', 'replace').rstrip()
            ext = e[8:11].decode('ascii', 'replace').rstrip()
            if ext:
                name += '.' + ext
            out.write(f'FAT entry name={name} attributes=0x{e[11]:02x} size={struct.unpack_from("<I", e, 28)[0]}\n')
    ext4 = data[154600*512+1024:154600*512+2048]
    out.write(f'partition 2 ext superblock magic={ext4[56:58].hex()} blocks={struct.unpack_from("<I", ext4, 4)[0]} log_block_size={struct.unpack_from("<I", ext4, 24)[0]}\n')
