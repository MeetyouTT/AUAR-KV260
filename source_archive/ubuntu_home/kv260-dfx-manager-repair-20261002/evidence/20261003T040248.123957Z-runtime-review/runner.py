#!/usr/bin/env python3
"""Remove build RPATH, check imports against the original image, and invoke only its loader."""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST_SDK = Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux')
IMAGE = Path('/home/ghmd/kv260-dpu41-control-20261001/evidence/baseline-rootfs.ext4')
CROSS = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dynsymbols(text):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[0].rstrip(':').isdigit():
            yield {'bind': parts[4], 'ndx': parts[6], 'name': parts[7]}


def main():
    run = ROOT / 'evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-runtime-review')
    run.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, str(run / 'runner.py'))
    out = ROOT / 'artifacts/runtime' / run.name
    image_root = run / 'image-runtime'
    assert not out.exists() and not image_root.exists()
    out.mkdir(parents=True)
    (image_root / 'lib').mkdir(parents=True)
    (image_root / 'usr/lib').mkdir(parents=True)
    status = {'scope': 'Offline original-image ABI and loader checks; manager never executed',
              'commands': [], 'image_libraries': [], 'binaries': [], 'passed': False}
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}

    def command(name, argv):
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=45)
        logfile = run / (name + '.log')
        logfile.write_text(p.stdout + p.stderr)
        status['commands'].append({'name': name, 'argv': argv, 'exit_code': p.returncode,
                                  'log': str(logfile.relative_to(ROOT)), 'sha256': sha(logfile)})
        assert p.returncode == 0, name + ': ' + p.stderr
        return p.stdout

    try:
        for source in ('/lib/libc.so.6', '/lib/libpthread.so.0', '/lib/ld-linux-aarch64.so.1', '/usr/lib/libdfx.so.1.0'):
            dest = image_root / source.lstrip('/')
            command('extract-' + dest.name, ['/sbin/debugfs', '-R', 'dump ' + source + ' ' + str(dest), str(IMAGE)])
            assert dest.is_file() and dest.read_bytes()[:4] == b'\x7fELF'
            # debugfs dump copies bytes, not the original executable mode.
            dest.chmod(0o755)
            status['image_libraries'].append({'image_path': source, 'host_path': str(dest),
                                             'bytes': dest.stat().st_size, 'sha256': sha(dest)})
        assert sha(image_root / 'usr/lib/libdfx.so.1.0') == sha(ROOT / 'deps/lib/libdfx.so.1.0')
        exports = set()
        provided_sonames = set()
        for library in sorted(image_root.rglob('*')):
            if not library.is_file():
                continue
            provided_sonames.add(library.name)
            text = command('symbols-' + library.name, [CROSS + 'readelf', '--dyn-syms', '--wide', str(library)])
            for s in dynsymbols(text):
                if s['ndx'] == 'UND' or s['bind'] not in ('GLOBAL', 'WEAK'):
                    continue
                exports.add(s['name'].replace('@@', '@'))
                if '@@' in s['name'] or '@' not in s['name']:
                    exports.add(s['name'].split('@')[0])
            dynamic = command('dynamic-' + library.name, [CROSS + 'readelf', '-d', str(library)])
            status.setdefault('library_dependencies', {})[library.name] = re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)
        assert all(n in provided_sonames for deps in status['library_dependencies'].values() for n in deps)
        for phase in ('baseline', 'patched'):
            (out / phase).mkdir()
            for name in ('dfx-mgrd', 'dfx-mgr-client'):
                binary = out / phase / name
                shutil.copy2(str(ROOT / 'artifacts' / phase / name), str(binary))
                command('remove-rpath-' + phase + '-' + name, [str(HOST_SDK / 'usr/bin/chrpath'), '-d', str(binary)])
                elf = command('elf-' + phase + '-' + name, [CROSS + 'readelf', '-h', '-l', '-d', '-V', str(binary)])
                assert 'AArch64' in elf and '/lib/ld-linux-aarch64.so.1' in elf
                assert not re.search(r'\((?:RPATH|RUNPATH)\)', elf)
                needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', elf)
                assert all(n in provided_sonames for n in needed)
                symbols = command('imports-' + phase + '-' + name,
                                  [CROSS + 'readelf', '--dyn-syms', '--wide', str(binary)])
                strong = sorted(s['name'] for s in dynsymbols(symbols) if s['ndx'] == 'UND' and s['bind'] == 'GLOBAL')
                unresolved = [s for s in strong if s not in exports]
                assert not unresolved, repr(unresolved)
                loader = command('loader-' + phase + '-' + name, [str(HOST_SDK / 'usr/bin/qemu-aarch64'),
                    '-L', str(image_root), str(image_root / 'lib/ld-linux-aarch64.so.1'),
                    '--inhibit-cache', '--library-path', str(image_root / 'usr/lib') + ':' + str(image_root / 'lib'),
                    '--list', str(binary)])
                assert 'not found' not in loader
                status['binaries'].append({'phase': phase, 'path': str(binary.relative_to(ROOT)),
                    'bytes': binary.stat().st_size, 'sha256': sha(binary), 'needed': needed,
                    'strong_imports': strong, 'unresolved_strong_imports': unresolved,
                    'build_rpath_removed': True, 'original_image_loader_list_passed': True})
        for phase in ('baseline', 'patched'):
            command('client-text-' + phase, [CROSS + 'objcopy', '--dump-section',
                    '.text=' + str(run / (phase + '-client.text')), str(out / phase / 'dfx-mgr-client')])
        status['client_text_unchanged'] = (run / 'baseline-client.text').read_bytes() == (run / 'patched-client.text').read_bytes()
        assert status['client_text_unchanged']
        status['passed'] = True
    except Exception as error:
        status['error'] = str(error)
    (run / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'passed': status['passed'], 'run': str(run), 'error': status.get('error'),
                      'binaries': [{k: b[k] for k in ('phase', 'path', 'bytes', 'sha256')} for b in status['binaries']]}), flush=True)
    return 0 if status['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
