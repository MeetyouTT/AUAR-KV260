#!/usr/bin/env python3
"""Prepare a KV260 cross SDK on Ubuntu using the offline rootfs and the installed Vitis 2022.2 tools."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def quoted(path):
    word = str(path)
    if any(c in word for c in '"\\\n\r'):
        raise ValueError('Unsupported debugfs path ' + word)
    return '"' + word + '"'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rootfs', type=Path, required=True, help='offline EXT4 partition file')
    ap.add_argument('--vitis-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True, help='fresh external SDK directory')
    ap.add_argument('--build-out', type=Path, help='also run the complete native build into a separate new directory')
    a = ap.parse_args()
    image = a.rootfs.resolve(strict=True)
    vitis = a.vitis_root.resolve(strict=True)
    out = a.out.resolve()
    if out == ROOT or ROOT in out.parents or out.exists():
        ap.error('--out must be a new directory outside the package')
    gnu = vitis / 'gnu/aarch64/lin/aarch64-linux'
    bindir = gnu / 'bin'
    gcc_lib = gnu / 'aarch64-xilinx-linux/usr/lib/aarch64-xilinx-linux/11.2.0'
    cmake = vitis / 'tps/lnx64/cmake-3.21.4'
    for source in [bindir / 'aarch64-linux-gnu-g++', gcc_lib / 'libgcc.a', gcc_lib / 'crtbeginS.o', cmake / 'bin/cmake']:
        if not source.is_file():
            ap.error('Missing Vitis 2022.2 SDK component ' + str(source))
    out.mkdir(parents=True)
    sysroot = out / 'sysroot'
    lib = sysroot / 'usr/lib'
    lib.mkdir(parents=True)
    (sysroot / 'lib').mkdir()
    (lib / 'x11').mkdir()

    def debug(*args):
        return subprocess.run(['debugfs'] + list(args) + [str(image)], check=True, capture_output=True, text=True)

    commands = []
    def rdump(source, dest):
        commands.append('rdump ' + quoted(source) + ' ' + quoted(dest))

    rdump('/usr/include', sysroot / 'usr')
    for directory in ('pkgconfig', 'glib-2.0', 'gcc'):
        rdump('/usr/lib/' + directory, lib)
    rdump('/usr/lib/x11/libMali.so.9.0', lib / 'x11')
    for base in ('/usr/lib', '/lib'):
        dest = sysroot / base.lstrip('/')
        for line in debug('-R', 'ls -p ' + base).stdout.splitlines():
            fields = line.split('/')
            if len(fields) < 7:
                continue
            name = fields[5]
            if not re.fullmatch(r'[\w.+-]+', name):
                continue
            if '.so' in name or re.fullmatch(r'[Scrt][\w-]*\.o', name) or name in {
                'libc_nonshared.a', 'libpthread_nonshared.a', 'libpthread.a', 'libdl.a', 'librt.a', 'libutil.a'
            }:
                rdump(base + '/' + name, dest)
    batch = out / 'read-development-files.txt'
    batch.write_text('\n'.join(commands) + '\n')
    run = debug('-f', str(batch))
    (out / 'debugfs.log').write_text(run.stdout + run.stderr)
    for p in sysroot.rglob('*'):
        if p.is_symlink() and os.readlink(str(p)).startswith('/'):
            target = sysroot / os.readlink(str(p)).lstrip('/')
            p.unlink()
            p.symlink_to(os.path.relpath(str(target), str(p.parent)))
    for p in [lib / 'libGLESv2.so', lib / 'libdl.a', lib / 'glib-2.0/include/glibconfig.h',
              sysroot / 'usr/include/vart/runner.hpp', lib / 'pkgconfig/gstreamer-app-1.0.pc']:
        if not p.is_file():
            raise RuntimeError('Missing target development input ' + str(p))
    cpp = sysroot / 'usr/include/c++/11.2.0'
    driver_dir = out / 'tools'
    driver_dir.mkdir()
    for command, compiler in [('cc', 'aarch64-linux-gnu-gcc'), ('cxx', 'aarch64-linux-gnu-g++')]:
        flags = ['-B' + str(gcc_lib) + '/', '-L' + str(gcc_lib), '--sysroot=' + str(sysroot),
                 '-Wl,-rpath-link,' + str(lib), '-Wl,-rpath-link,' + str(sysroot / 'lib')]
        if command == 'cxx':
            flags += ['-isystem', str(cpp), '-isystem', str(cpp / 'aarch64-xilinx-linux')]
        path = driver_dir / command
        path.write_text('#!/bin/sh\nexec ' + ' '.join(shlex.quote(str(v)) for v in [bindir / compiler] + flags) + ' "$@"\n')
        path.chmod(0o755)
    toolchain = out / 'aarch64.cmake'
    toolchain.write_text('set(CMAKE_SYSTEM_NAME Linux)\nset(CMAKE_SYSTEM_PROCESSOR aarch64)\n'
                         'set(CMAKE_SYSROOT "{}")\nset(CMAKE_C_COMPILER "{}")\nset(CMAKE_CXX_COMPILER "{}")\n'
                         'set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)\nset(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)\n'
                         'set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)\n'.format(sysroot, driver_dir/'cc', driver_dir/'cxx'))
    env = os.environ.copy()
    settings = dict(CC=str(driver_dir/'cc'), CXX=str(driver_dir/'cxx'), CMAKE_TOOLCHAIN_FILE=str(toolchain),
                    PKG_CONFIG_SYSROOT_DIR=str(sysroot), PKG_CONFIG_LIBDIR=str(lib/'pkgconfig'),
                    PATH=str(cmake/'bin') + ':' + env['PATH'],
                    LD_LIBRARY_PATH=str(cmake/'libs/Ubuntu') + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else ''))
    (out / 'build_env.json').write_text(json.dumps(settings, indent=2) + '\n')
    if a.build_out:
        env.update(settings)
        subprocess.run(['sh', str(ROOT/'build/build_native.sh'), str(a.build_out.resolve())], env=env, check=True)
    print('Cross SDK prepared', out)


if __name__ == '__main__':
    main()

