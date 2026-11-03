#!/usr/bin/env python3
"""Run real helper/parser/inotify regression; hardware calls are explicit stubs."""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST_SDK = Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux')
MODES = ('rescan', 'parent-delete', 'active-lifecycle', 'events', 'lifecycle', 'boundaries', 'list-capacity', 'concurrent')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run = ROOT / 'evidence' / (stamp + '-host-tests')
    run.mkdir(exist_ok=False)
    shutil.copy2(__file__, run / 'runner.py')
    shutil.copy2(ROOT / 'tests/state_regression.c', run / 'state_regression.c')
    inputs = json.loads((ROOT / 'evidence/validation_inputs.json').read_text())
    headers = inputs['original_build_headers']
    source = ROOT / 'sources/dfx-mgr-patched'
    source_hashes = {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    status = {'scope': 'Native actual helper/parser and Linux inotify; FPGA API calls are test doubles',
              'source_sha256': source_hashes, 'commands': [], 'passed': False,
              'sanitizers': {}, 'fixture_paths': [], 'hardware_verified': False}
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
           'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
           'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1',
           'TSAN_OPTIONS': 'halt_on_error=1:exitcode=66'}

    def save():
        (run / 'status.json').write_text(json.dumps(status, indent=2) + '\n')

    def command(name, argv, timeout=120, optional_tsan=False):
        logfile = run / (name + '.log')
        start = time.monotonic()
        print('START', name, flush=True)
        try:
            with logfile.open('wb') as stream:
                result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
        data = logfile.read_text(errors='replace')
        record = {'name': name, 'argv': argv, 'exit_code': code,
                  'elapsed_seconds': round(time.monotonic() - start, 3),
                  'log': str(logfile.relative_to(ROOT)), 'sha256': sha(logfile),
                  'results': [line for line in data.splitlines() if line.startswith('RESULT ')]}
        status['commands'].append(record)
        unavailable = optional_tsan and 'FATAL: ThreadSanitizer: unexpected memory mapping' in data
        if unavailable:
            status['sanitizers']['tsan'] = {'state': 'runtime_unavailable', 'reason': data.strip()}
        save()
        print('END', name, code, flush=True)
        if code and not unavailable:
            print('\n'.join(data.splitlines()[-35:]), flush=True)
            raise RuntimeError(name + ' failed; exit ' + str(code))
        return not unavailable

    def compile_binary(label, compiler, src, flags=(), legacy=False):
        binary = run / ('regression-' + label)
        args = [compiler, '-O1', '-g', '-ffunction-sections', '-fdata-sections',
                '-fno-omit-frame-pointer', '-pthread', '-no-pie', '-I' + headers,
                '-I' + str(src / 'include'), '-DHELPER_FILE="' + str(src / 'src/daemon_helper.c') + '"']
        if legacy:
            args.append('-DLEGACY_SOURCE=1')
        args += list(flags) + [str(run / 'state_regression.c'), str(src / 'src/sys/linux/json-config.c'),
                              str(src / 'src/sys/linux/print.c'), str(src / 'src/assert.c'),
                              '-Wl,--gc-sections', '-o', str(binary)]
        command('compile-' + label, args)
        return binary

    try:
        command('system-compiler', ['/usr/bin/gcc', '--version'])
        legacy = compile_binary('legacy', str(HOST_SDK / 'usr/bin/x86_64-petalinux-linux-gcc'),
                                ROOT / 'sources/dfx-mgr', legacy=True)
        normal = compile_binary('native', '/usr/bin/gcc', source)
        sanitized = compile_binary('asan-ubsan', '/usr/bin/gcc', source,
                                   ('-fsanitize=address,undefined',))
        # Short temporary paths exercise valid packages within vendor tmp_dir[128].
        with tempfile.TemporaryDirectory(prefix='dfxsv-', dir='/tmp') as temporary:
            status['fixture_paths'].append(temporary)
            command('legacy-delete', [str(legacy), 'legacy-delete', temporary + '/legacy'])
            for label, binary in (('native', normal), ('asan-ubsan', sanitized)):
                for i, mode in enumerate(MODES):
                    fixture = temporary + '/' + label + '-' + str(i)
                    command(label + '-' + mode, [str(binary), mode, fixture])
            status['sanitizers']['asan_ubsan'] = {'state': 'passed', 'cases': len(MODES), 'leak_detection': True}
            tsan = compile_binary('tsan', '/usr/bin/gcc', source, ('-fsanitize=thread',))
            tsan_ok = command('tsan-concurrent', [str(tsan), 'concurrent', temporary + '/tsan'], optional_tsan=True)
            if tsan_ok:
                status['sanitizers']['tsan'] = {'state': 'passed', 'cases': 1}
        assert source_hashes == {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
        status['passed'] = True
        status['native_cases_passed'] = len(MODES)
        status['legacy_parent_delete_reproduced'] = True
    except Exception as error:
        status['error'] = str(error)
    save()
    if status['passed']:
        (ROOT / 'CURRENT_HOST_TESTS.json').write_text(json.dumps({
            'run': str(run), 'status_file': str(run / 'status.json'),
            'source_sha256': source_hashes, 'sanitizers': status['sanitizers']
        }, indent=2) + '\n')
    print(json.dumps({'passed': status['passed'], 'run': str(run),
                      'sanitizers': status['sanitizers'], 'error': status.get('error')}), flush=True)
    return 0 if status['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
