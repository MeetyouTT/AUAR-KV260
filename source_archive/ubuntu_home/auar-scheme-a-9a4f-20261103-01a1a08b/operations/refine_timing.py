#!/usr/bin/env python3
"""Refine a completed, timing-limited cold run using only its own checked checkpoints."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
from reproduce import hw_sources


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior', type=Path, required=True, help='cold hardware run output')
    p.add_argument('--out', type=Path, required=True, help='fresh external recovery output')
    p.add_argument('--vivado', type=Path, required=True)
    a = p.parse_args()
    prior = a.prior.resolve(strict=True)
    out = a.out.resolve()
    if out.exists() or ROOT in out.parents or out == ROOT or prior in out.parents or ROOT in prior.parents:
        p.error('select separate, external prior/output directories')
    before = hw_sources()
    prep = read(prior / 'prepare.receipt.json')
    first = read(prior / 'implement.receipt.json')
    log = prior / 'implement.console.log'
    if prep['status'] != 'PASS' or first['status'] != 'FAIL':
        raise ValueError('This entry requires a passed preparation and a measured, failed implementation')
    if prep['hardware_source_sha256'] != before or first['hardware_source_sha256'] != before or sha(log) != first['log_sha256']:
        raise ValueError('Cold-run inputs or logs do not match this source tree')
    writer = read(prior / 'hardware/reports/implementation.json')
    text = log.read_text(errors='replace')
    if 'AUAR_BUILD_FAILED: Implementation timing/DRC failed' not in text or writer['drc_errors'] != 0 or min(writer['wns_ns'], writer['whs_ns']) >= 0:
        raise ValueError('Original failure is not a measured timing-only failure')
    subprocess.run([sys.executable, '-B', str(ROOT/'build/rtl_results.py'), 'verify', '--root', str(ROOT),
                    '--result', str(prior/'rtl/result.json')], check=True)
    paths = [prior/'hardware'/n for n in ['source_synth.dcp', 'source_placed.dcp']]
    pins = {}
    for f in paths:
        if f.is_symlink() or not f.is_file() or str(f) not in text:
            raise ValueError('Missing provenance for locally generated checkpoint ' + f.name)
        pins[f.name] = sha(f)
    scripts = [ROOT/'build/refine_timing.py', ROOT/'build/refine_timing.tcl']
    deps = {f.relative_to(ROOT).as_posix(): sha(f) for f in scripts}
    out.mkdir(parents=True)
    executable = a.vivado.resolve(strict=True)
    env = dict(os.environ, LC_ALL='C', LANG='C', PYTHONDONTWRITEBYTECODE='1', XILINX_VIVADO=str(executable.parent.parent))
    env['PATH'] = str(executable.parent) + ':' + env.get('PATH', '')
    command = [str(executable), '-mode', 'batch', '-nojournal', '-nolog', '-source', str(scripts[1]), '-tclargs',
               str(prior/'hardware'), str(out/'hardware')]
    started = time.monotonic()
    output = out/'implement.console.log'
    with output.open('xb') as stream:
        result = subprocess.run(command, cwd=str(out), env=env, stdout=stream, stderr=subprocess.STDOUT)
    passed = result.returncode == 0 and 'AUAR_REFINE_PASS' in output.read_text(errors='replace').splitlines()
    passed = passed and hw_sources() == before and all(sha(f) == pins[f.name] for f in paths)
    passed = passed and all(sha(f) == deps[f.relative_to(ROOT).as_posix()] for f in scripts)
    passed = passed and all((out/'hardware'/n).is_file() and (out/'hardware'/n).stat().st_size
                            for n in ['auar_source.bit', 'auar_source.xsa', 'reports/implementation.json'])
    receipt = {'stage': 'implement', 'status': 'PASS' if passed else 'FAIL', 'commands': [{'argv': command, 'exit_code': result.returncode}],
               'tool': str(executable), 'elapsed_seconds': round(time.monotonic() - started, 3),
               'hardware_source_sha256': dict(before, **deps), 'log_sha256': sha(output),
               'prior_checkpoint_sha256': pins, 'prior_implementation': writer,
               'prior_implementation_receipt_sha256': sha(prior/'implement.receipt.json'),
               'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'board_accessed': False}
    (out/'implement.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'], out/'implement.receipt.json')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

