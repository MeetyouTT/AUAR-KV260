#!/usr/bin/env python3
"""Read selected factory-image evidence without mounting or modifying the image."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
IMAGE = ROOT.parent / 'kv260-dpu41-control-20261001/evidence/baseline-rootfs.ext4'
KERNEL = ROOT.parent / 'AMD_Smart/logs/fpga/2026-09-30-kv260-readonly/baseline-host-image-boot/Image'
OUTPUT = ROOT / 'evidence/image_files'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit('Refusing to overwrite extracted image evidence')
    OUTPUT.mkdir(parents=True)
    records = []
    for source, name in [
        ('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko', 'zocl.ko'),
        ('/usr/lib/libxrt_core.so.2.14.0', 'libxrt_core.so.2.14.0'),
        ('/usr/bin/dfx-mgrd', 'dfx-mgrd'),
        ('/usr/lib/libdfx.so.1.0', 'libdfx.so.1.0'),
    ]:
        destination = OUTPUT / name
        command = ['debugfs', '-R', 'dump ' + source + ' ' + str(destination), str(IMAGE)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log = OUTPUT / (name + '.dump.log')
        log.write_text(result.stdout + result.stderr)
        present = destination.is_file() and destination.stat().st_size > 0
        if present and destination.read_bytes()[:4] != b'\x7fELF':
            raise RuntimeError('Expected a regular ELF file: ' + name)
        records.append({'image_path': source, 'host_path': str(destination.relative_to(ROOT)),
                        'command': command, 'debugfs_returncode': result.returncode,
                        'extracted_regular_elf': present,
                        'bytes': destination.stat().st_size if present else None,
                        'sha256': sha(destination) if present else None})
    kernel_bytes = KERNEL.read_bytes()
    start = kernel_bytes.find(b'IKCFG_ST')
    end = kernel_bytes.find(b'IKCFG_ED', start + 8) if start >= 0 else -1
    kernel_record = {'source': str(KERNEL), 'bytes': len(kernel_bytes), 'sha256': sha(KERNEL),
                     'embedded_config_present': start >= 0 and end > start}
    if kernel_record['embedded_config_present']:
        config = gzip.decompress(kernel_bytes[start + 8:end])
        path = OUTPUT / 'kernel.config'
        path.write_bytes(config)
        kernel_record.update({'config_path': str(path.relative_to(ROOT)), 'config_sha256': sha(path)})
    metadata = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Offline factory image, not current live board inventory',
                'rootfs_image': str(IMAGE), 'rootfs_image_bytes': IMAGE.stat().st_size,
                'image_opened_read_only': True, 'files': records, 'kernel': kernel_record}
    (OUTPUT / 'extraction.json').write_text(json.dumps(metadata, indent=2) + '\n')
    for record in records:
        print(record['image_path'], 'EXTRACTED' if record['extracted_regular_elf'] else 'NOT FOUND', record['sha256'])
    print('EMBEDDED_KERNEL_CONFIG', kernel_record['embedded_config_present'])


if __name__ == '__main__':
    main()
