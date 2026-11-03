#!/usr/bin/env python3
"""Build the person detector bridge natively on the KV260; install no packages."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).with_name('yolox_bridge.cpp'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if platform.machine() != 'aarch64':
        raise RuntimeError('Build this bridge on the reviewed aarch64 target')
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    include = subprocess.check_output(['pkg-config', '--cflags', 'opencv4'], text=True)
    command = ['g++', '-std=c++17', '-O2', '-fPIC', '-shared', '-Wl,-z,defs',
               *shlex.split(include), str(args.source), '-o', str(args.output),
               '-lvitis_ai_library-yolovx', '-lvitis_ai_library-dpu_task', '-lopencv_core', '-lglog']
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    if completed.returncode:
        raise RuntimeError(completed.stdout[-8000:])
    print(json.dumps({'status': 'PASS', 'machine': platform.machine(), 'command': command,
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'library_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'library_bytes': args.output.stat().st_size,
        'dependencies': subprocess.check_output(['ldd', str(args.output)], text=True)}))


if __name__ == '__main__':
    main()
