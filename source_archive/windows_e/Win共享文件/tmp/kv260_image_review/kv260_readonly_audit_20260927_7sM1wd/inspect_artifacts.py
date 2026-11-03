import gzip
import hashlib
import io
import os
import struct
import zipfile
from pathlib import Path

AUD = Path('/home/ghmd/kv260_readonly_audit_20260927_7sM1wd')
paths = [
    '/home/ghmd/work/kv260_dpu_b2304_uram/output/kv260_dpu.bit',
    '/home/ghmd/work/kv260_dpu_b2304_uram/output/kv260_dpu.xsa',
    '/home/ghmd/work/kv260_dpu_b2304_uram/output/kv260_dpu_clockfix.xsa',
    '/home/ghmd/work/kv260_dpu_clockfix_hw/system.xsa',
    '/home/ghmd/kv260_clockfix_rebuild_20260926/artifacts/kv260_dpu_clockfix_rebuilt.bit',
    '/home/ghmd/kv260_clockfix_rebuild_20260926/artifacts/kv260_dpu_clockfix_rebuilt.xsa',
    '/home/ghmd/work/petalinux-kv260-dpu/project-spec/hw-description/system.xsa',
    '/home/ghmd/work/petalinux-kv260-dpu/project-spec/hw-description/kv260_dpu_clockfix.bit',
    '/home/ghmd/work/petalinux-kv260-dpu/images/linux/system.bit',
    '/home/ghmd/work/petalinux-kv260-dpu/images/linux/system.dtb',
    '/home/ghmd/work/petalinux-kv260-dpu/images/linux/BOOT.BIN',
    '/home/ghmd/work/petalinux-kv260-dpu/images/linux/image.ub',
    '/home/ghmd/work/petalinux-kv260-dpu/images/linux/rootfs.cpio.gz',
    '/home/ghmd/work/models/resnet50-b2304/compiled/resnet50_b2304.xmodel',
    '/home/ghmd/kv260_resnet50_verified_rebuild_20260926/compiled/resnet50_b2304_verified.xmodel',
    '/home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.gen/sources_1/bd/kv260_dpu_bd/ip/kv260_dpu_bd_dpu_0_0/arch.json',
]

def hashstream(f):
    h = hashlib.sha256()
    while chunk := f.read(4 * 1024 * 1024):
        h.update(chunk)
    return h.hexdigest()

with (AUD / 'logs/artifact_hashes.tsv').open('w') as out:
    out.write('path\tsize\tsha256\n')
    for p in paths:
        path = Path(p)
        if not path.is_file():
            out.write(f'{p}\tMISSING\t\n')
            continue
        with path.open('rb') as f:
            sha = hashstream(f)
        out.write(f'{p}\t{path.stat().st_size}\t{sha}\n')

with (AUD / 'logs/xsa_members.tsv').open('w') as out:
    out.write('xsa\tmember\tsize\tsha256\n')
    for p in paths:
        if not p.endswith('.xsa') or not Path(p).is_file():
            continue
        try:
            with zipfile.ZipFile(p) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    if info.filename.lower().endswith(('.bit', '.hwh', '.xml', '.json')):
                        with z.open(info) as f:
                            sha = hashstream(f)
                        out.write(f'{p}\t{info.filename}\t{info.file_size}\t{sha}\n')
                bad = z.testzip()
                out.write(f'{p}\tZIP_TEST\t\t{bad or "OK"}\n')
        except Exception as e:
            out.write(f'{p}\tZIP_ERROR\t\t{type(e).__name__}: {e}\n')

img = Path('/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz')
with (AUD / 'logs/official_image_partition_header.txt').open('w') as out:
    with gzip.open(img, 'rb') as f:
        head = f.read(34 * 512)
    out.write(f'first {len(head)} decompressed bytes\n')
    out.write(f'MBR signature: {head[510:512].hex()}\n')
    for i in range(4):
        e = head[446+i*16:462+i*16]
        out.write(f'MBR[{i}]: type=0x{e[4]:02x} start_lba={struct.unpack_from("<I", e, 8)[0]} sectors={struct.unpack_from("<I", e, 12)[0]}\n')
    out.write(f'GPT signature: {head[512:520]!r}\n')
