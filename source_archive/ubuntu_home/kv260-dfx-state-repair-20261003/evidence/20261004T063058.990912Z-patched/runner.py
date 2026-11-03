#!/usr/bin/env python3
"""Build preserved baseline or candidate with the existing SDK; retain every run."""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux')
CROSS = str(SDK / 'bin/aarch64-linux-gnu-')
CMAKE = str(SDK / 'x86_64-petalinux-linux/usr/bin/cmake')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    phase = sys.argv[1]
    assert phase in ('baseline', 'patched')
    source = ROOT / 'sources' / ('dfx-mgr' if phase == 'baseline' else 'dfx-mgr-patched')
    run = ROOT / 'evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + phase)
    artifacts = ROOT / 'artifacts' / phase / run.name
    run.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, str(run / 'runner.py'))
    build = ROOT / 'build' / run.name
    assert not build.exists() and not artifacts.exists(), 'Refusing to overwrite a previous build'
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('PETALINUX', 'XILINX', 'OECORE', 'SDKTARGET')) or key in (
            'LD_LIBRARY_PATH', 'LIBRARY_PATH', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH',
            'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'MAKEFLAGS', 'MFLAGS', 'CC', 'CXX'):
            env.pop(key, None)
    env.update({'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    source_hashes = {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    status = {'phase': phase, 'source': str(source), 'source_sha256': source_hashes,
              'artifact_dir': str(artifacts), 'build': str(build), 'commands': [], 'jobs': 4, 'passed': False}

    def command(name, argv):
        start = time.monotonic()
        print('START', name, flush=True)
        logfile = run / (name + '.log')
        with logfile.open('wb') as stream:
            result = subprocess.run(argv, cwd=str(ROOT), env=env, stdout=stream, stderr=subprocess.STDOUT)
        status['commands'].append({'name': name, 'argv': argv, 'cwd': str(ROOT),
                                  'exit_code': result.returncode, 'log': str(logfile.relative_to(ROOT)),
                                  'sha256': sha(logfile), 'elapsed_seconds': round(time.monotonic() - start, 3)})
        (run / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
        print('END', name, result.returncode, str(logfile), flush=True)
        if result.returncode:
            print('\n'.join(logfile.read_text(errors='replace').splitlines()[-25:]), flush=True)
            raise RuntimeError(name + ' failed')

    try:
        command('compiler', [CROSS + 'gcc', '--version'])
        command('cmake-version', [CMAKE, '--version'])
        command('configure', [CMAKE, '-S', str(source), '-B', str(build), '-G', 'Unix Makefiles',
            '-DCMAKE_SYSTEM_NAME=Linux', '-DCMAKE_SYSTEM_PROCESSOR=aarch64',
            '-DCMAKE_C_COMPILER=' + CROSS + 'gcc', '-DCMAKE_ASM_COMPILER=' + CROSS + 'gcc',
            '-DCMAKE_SYSROOT=' + str(SDK / 'aarch64-xilinx-linux'),
            '-DCMAKE_INCLUDE_PATH=' + str(ROOT / 'deps/include'),
            '-DCMAKE_LIBRARY_PATH=' + str(ROOT / 'deps/lib'), '-D_deps=dfx',
            '-DCMAKE_BUILD_TYPE=Debug', '-DWITH_STATIC_LIB=ON', '-DWITH_SHARED_LIB=OFF',
            '-DCMAKE_C_FLAGS=-O2 -fPIC -fstack-protector-strong -D_FORTIFY_SOURCE=2 -mbranch-protection=standard',
            '-DCMAKE_EXE_LINKER_FLAGS=-Wl,-z,relro,-z,now'])
        command('compile', [CMAKE, '--build', str(build), '--parallel', '4', '--target',
                            'dfx-mgrd-static', 'dfx-mgr-client-static'])
        artifacts.mkdir(parents=True, exist_ok=False)
        for name in ('dfx-mgrd', 'dfx-mgr-client'):
            source_binary = build / 'example/sys/linux' / (name + '-static')
            shutil.copy2(str(source_binary), str(artifacts / (name + '.debug')))
            shutil.copy2(str(source_binary), str(artifacts / name))
            command('strip-' + name, [CROSS + 'strip', '--strip-debug', str(artifacts / name)])
            command('elf-' + name, [CROSS + 'readelf', '-h', '-l', '-d', '-V', '-Ws', str(artifacts / name)])
        assert source_hashes == {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}, 'Source changed during build'
        status['artifacts'] = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
                               for p in sorted(artifacts.iterdir())}
        status['passed'] = True
    except Exception as error:
        status['error'] = str(error)
    (run / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    if status['passed']:
        (ROOT / ('CURRENT_BUILD_' + phase.upper() + '.json')).write_text(json.dumps({
            'run': str(run), 'status_file': str(run / 'status.json'),
            'artifact_dir': str(artifacts), 'source_sha256': source_hashes
        }, indent=2) + '\n')
    print(json.dumps({'passed': status['passed'], 'run': str(run), 'error': status.get('error')}), flush=True)
    return 0 if status['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
