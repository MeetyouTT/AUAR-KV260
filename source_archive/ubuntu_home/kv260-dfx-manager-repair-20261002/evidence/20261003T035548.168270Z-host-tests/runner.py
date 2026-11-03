#!/usr/bin/env python3
"""Record native tests of the real helper and JSON parser, using host inotify."""
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


def main():
    run = ROOT / 'evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-host-tests')
    run.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, str(run / 'runner.py'))
    shutil.copy2(str(ROOT / 'tests/watch_regression.c'), str(run / 'watch_regression.c'))
    status = {'scope': 'Native helper tests; no board, FPGA access, daemon or app loading',
              'commands': [], 'passed': False}
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
           'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1'}

    def command(name, argv, timeout=90):
        logfile = run / (name + '.log')
        start = time.monotonic()
        with logfile.open('wb') as f:
            result = subprocess.run(argv, cwd=str(ROOT), env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
        data = logfile.read_bytes()
        status['commands'].append({'name': name, 'argv': argv, 'exit_code': result.returncode,
                                  'elapsed_seconds': round(time.monotonic() - start, 3),
                                  'log': str(logfile.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(),
                                  'result_lines': [x for x in data.decode(errors='replace').splitlines() if x.startswith('RESULT ')]})
        (run / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
        print(name, 'exit', result.returncode, 'log', str(logfile), flush=True)
        if result.returncode:
            print('\n'.join(data.decode(errors='replace').splitlines()[-20:]), flush=True)
            raise RuntimeError(name + ' failed')

    try:
        for phase in ('baseline', 'patched'):
            src = ROOT / 'sources' / ('dfx-mgr' if phase == 'baseline' else 'dfx-mgr-patched')
            builds = [json.loads(p.read_text()) for p in ROOT.glob('evidence/*-' + phase + '/status.json')]
            good = [b for b in builds if b['passed']]
            assert len(good) == 1
            headers = Path(good[0]['build']) / 'src/include'
            binary = run / ('watch-' + phase)
            argv = ['gcc', '-O1', '-g', '-ffunction-sections', '-fdata-sections', '-fno-omit-frame-pointer',
                    '-fsanitize=address,undefined', '-pthread', '-I' + str(headers), '-I' + str(src / 'include'),
                    '-DHELPER_FILE="' + str(src / 'src/daemon_helper.c') + '"',
                    str(run / 'watch_regression.c'), str(src / 'src/sys/linux/json-config.c'),
                    str(src / 'src/sys/linux/print.c'), str(src / 'src/assert.c'),
                    '-Wl,--gc-sections', '-o', str(binary)]
            command('compile-' + phase, argv)
            modes = ('legacy',) if phase == 'baseline' else ('rescan', 'lifecycle', 'boundaries', 'concurrent')
            for mode in modes:
                command(phase + '-' + mode, [str(binary), mode, str(run / ('fixture-' + mode))])
        status['passed'] = True
    except Exception as error:
        status['error'] = str(error)
    (run / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'passed': status['passed'], 'run': str(run), 'error': status.get('error')}), flush=True)
    return 0 if status['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
