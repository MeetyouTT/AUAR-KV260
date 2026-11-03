#!/usr/bin/env python3
"""Validate the frozen motor candidate using fake hardware and RTL simulation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'candidate'
SETTINGS = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh'
CROSS = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rtl-only', action='store_true')
    parser.add_argument('--compile-only', action='store_true')
    parser.add_argument('--tops', nargs='+', choices=['tb_pulse_guard', 'tb_servo', 'tb_nominal'])
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    os.nice(15)
    out = ROOT / (args.output or ('validation-rtl' if args.rtl_only else 'validation'))
    out.mkdir()
    results = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(CANDIDATE / 'runtime/aura') + ':' + str(CANDIDATE / 'runtime/aura/tests/framework'))

    def run(label, argv, cwd=out, marker=None, xilinx=False):
        if xilinx:
            argv = ['bash', '--noprofile', '--norc', '-c',
                    'set -e; source "$1"; shift; exec "$@"', 'aura-pan-check', SETTINGS, *map(str, argv)]
        log_path = out / (label + '.log')
        with log_path.open('wb') as log:
            process = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        content = log_path.read_text(errors='replace')
        passed = process.returncode == 0 and (marker is None or marker in content)
        results.append({'label': label, 'returncode': process.returncode, 'passed': passed,
                        'log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest()})
        (out / 'results.json').write_text(json.dumps({'passed': all(r['passed'] for r in results),
            'board_accessed': False, 'native_library_executed': False, 'results': results}, indent=2) + '\n')
        print(label, 'PASS' if passed else 'FAIL', flush=True)
        if not passed:
            raise RuntimeError(label + ' failed; see ' + str(log_path))

    if not args.rtl_only:
        run('safe-completion', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', CANDIDATE / 'tests', '-p', 'test_safe_completion.py', '-v'])
        run('manual-regression', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', CANDIDATE / 'runtime/aura/tests/framework', '-p', 'test_manual_pan*.py', '-v'])
        run('native', [sys.executable, '-B', CANDIDATE / 'scripts/build_native.py', '--cross-cc', CROSS, '--out', out / 'native'])
    for top, marker in [('tb_pulse_guard', 'AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE'),
                        ('tb_servo', 'AURA_SERVO_TEST_PASS'),
                        ('tb_nominal', 'AURA_NOMINAL_TEST_PASS')]:
        if args.tops and top not in args.tops:
            continue
        directory = out / top
        directory.mkdir()
        run(top + '-compile', ['xvlog', '-sv', CANDIDATE / 'rtl/visual_servo.sv', CANDIDATE / ('tests/' + top + '.sv')], cwd=directory, xilinx=True)
        run(top + '-elaborate', ['xelab', top, '-s', top + '_snapshot', '-mt', 'off'], cwd=directory, xilinx=True)
        if not args.compile_only:
            run(top + '-simulate', ['xsim', top + '_snapshot', '-runall'], cwd=directory, marker=marker, xilinx=True)


if __name__ == '__main__':
    main()
