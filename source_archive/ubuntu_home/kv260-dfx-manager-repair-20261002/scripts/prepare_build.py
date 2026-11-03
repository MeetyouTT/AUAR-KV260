#!/usr/bin/env python3
"""Prepare isolated build inputs; never install software or modify the board."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux')
CROSS = SDK / 'bin/aarch64-linux-gnu-'
CMAKE = SDK / 'x86_64-petalinux-linux/usr/bin/cmake'
IMAGE = Path('/home/ghmd/kv260-dpu41-control-20261001/evidence/baseline-rootfs.ext4')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def main():
    deps = ROOT / 'deps'
    assert not deps.exists(), 'Refusing to overwrite dependency staging'
    (deps / 'include/libdrm').mkdir(parents=True)
    (deps / 'lib').mkdir()
    records = []
    originals = [
        (ROOT / 'sources/libdfx/src/include/libdfx.h', deps / 'include/libdfx.h'),
        (Path('/home/ghmd/kv260-overlay-repair-20261002/evidence/image_files/libdfx.so.1.0'), deps / 'lib/libdfx.so.1.0'),
    ]
    originals += [(p, deps / 'include/libdrm' / p.name)
                  for p in sorted((SDK / 'aarch64-xilinx-linux/usr/include/drm').glob('*.h'))]
    for original, dest in originals:
        shutil.copy2(str(original), str(dest))
        assert sha(original) == sha(dest)
        records.append({'input': str(original), 'staged': str(dest.relative_to(ROOT)),
                        'bytes': dest.stat().st_size, 'sha256': sha(dest)})
    (deps / 'lib/libdfx.so').symlink_to('libdfx.so.1.0')
    shutil.copytree(str(ROOT / 'sources/dfx-mgr'), str(ROOT / 'sources/dfx-mgr-patched'))
    (ROOT / 'evidence/build_inputs.json').write_text(json.dumps({
        'compiler_prefix': str(CROSS), 'cmake': str(CMAKE), 'sysroot': str(SDK / 'aarch64-xilinx-linux'),
        'dependencies': records, 'note': 'Original libdfx binary is a link-time input, not a new build artifact.'
    }, indent=2) + '\n')
    print(json.dumps({'dependency_files': len(records), 'isolated_patched_source_prepared': True}))


if __name__ == '__main__':
    main()
