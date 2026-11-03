#!/usr/bin/env python3
"""Refine setup/hold margins from a completed source-generated AUAR implementation."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from reproduce import hw_sources

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    temp = path.with_name(path.name + '.writing')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(str(temp), str(path))


def inputs():
    result = hw_sources()
    for name in ['build/refine_timing.py', 'build/refine_timing.tcl', 'build/env.json']:
        result[name] = sha(ROOT / name)
    return result


def main():
    defaults = read_json(ROOT / 'build/env.json')['final_timing_margins_ns']
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True,
                        help='completed build/reproduce.py output directory')
    parser.add_argument('--out', type=Path, required=True, help='fresh external output directory')
    parser.add_argument('--vivado', help='Vivado 2022.2 executable')
    parser.add_argument('--setup-min-ns', type=float, default=defaults['setup'])
    parser.add_argument('--hold-min-ns', type=float, default=defaults['hold'])
    args = parser.parse_args()
    for value in [args.setup_min_ns, args.hold_min_ns]:
        if not math.isfinite(value) or value < 0:
            parser.error('margins must be finite, nonnegative values in ns')
    baseline = args.baseline.resolve(strict=True)
    out = args.out.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents:
        parser.error('choose a fresh output directory outside the package')
    receipt_path = baseline / 'implement.receipt.json'
    prepared_path = baseline / 'prepare.receipt.json'
    receipt = read_json(receipt_path)
    prepared = read_json(prepared_path)
    source_pins = hw_sources()
    if receipt.get('status') != 'PASS' or prepared.get('status') != 'PASS':
        raise ValueError('baseline prepare and implementation must have completed successfully')
    if receipt.get('hardware_source_sha256') != source_pins or prepared.get('hardware_source_sha256') != source_pins:
        raise ValueError('baseline source files differ from the current hardware sources')
    checkpoint = baseline / 'hardware/auar_source_routed.dcp'
    if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        raise ValueError('the source-generated routed checkpoint is missing')
    rtl = baseline / 'rtl/result.json'
    subprocess.run([sys.executable, '-B', str(ROOT / 'build/rtl_results.py'),
                    'verify', '--root', str(ROOT), '--result', str(rtl)], check=True)
    executable = Path(args.vivado or shutil.which('vivado') or '/nonexistent/vivado').resolve()
    if not executable.is_file():
        parser.error('select the Vivado 2022.2 executable with --vivado')
    disk_parent = out.parent
    while not disk_parent.exists():
        disk_parent = disk_parent.parent
    if shutil.disk_usage(str(disk_parent)).free < 1024 ** 3:
        raise ValueError('at least 1 GiB of free output space is required before refinement')
    out.mkdir(parents=True)
    before = inputs()
    checkpoint_sha = sha(checkpoint)
    baseline_record = {
        'checkpoint': str(checkpoint),
        'checkpoint_sha256': checkpoint_sha,
        'implementation_receipt_sha256': sha(receipt_path),
        'prepare_receipt_sha256': sha(prepared_path),
        'source_sha256': source_pins,
        'implementation': read_json(baseline / 'hardware/reports/implementation.json')
    }
    save(out / 'baseline.json', baseline_record)
    save(out / 'inputs.before.json', before)
    hardware = out / 'hardware'
    command = [
        str(executable), '-mode', 'batch', '-nojournal', '-nolog',
        '-source', str(ROOT / 'build/refine_timing.tcl'), '-tclargs',
        '--root', str(ROOT), '--checkpoint', str(checkpoint), '--out', str(hardware),
        '--rtl-results', str(rtl), '--setup-min-ns', str(args.setup_min_ns),
        '--hold-min-ns', str(args.hold_min_ns)
    ]
    env = os.environ.copy()
    env.update(XILINX_VIVADO=str(executable.parent.parent),
               PYTHONDONTWRITEBYTECODE='1', LC_ALL='C', LANG='C')
    env['PATH'] = str(executable.parent) + os.pathsep + env.get('PATH', '')
    log = out / 'implement.console.log'
    started = time.monotonic()
    with log.open('xb') as output:
        completed = subprocess.run(command, cwd=str(out), env=env,
                                   stdout=output, stderr=subprocess.STDOUT)
    source_unchanged = inputs() == before
    checkpoint_unchanged = sha(checkpoint) == checkpoint_sha
    result_path = hardware / 'reports/implementation.json'
    metrics = read_json(result_path) if result_path.is_file() else None
    qualified = (
        completed.returncode == 0
        and source_unchanged
        and checkpoint_unchanged
        and 'AUAR_MARGIN_PASS' in log.read_text(errors='replace').splitlines()
        and metrics is not None
        and metrics['wns_ns'] >= args.setup_min_ns
        and metrics['whs_ns'] >= args.hold_min_ns
        and metrics['drc_errors'] == 0
        and metrics['routing_errors'] == 0
        and metrics['original_user_uncertainty_restored'] is True
        and all((hardware / name).is_file() and (hardware / name).stat().st_size
                for name in ['auar_source.bit', 'auar_source.xsa'])
    )
    result = {
        'stage': 'margin_refinement',
        'status': 'PASS' if qualified else 'FAIL',
        'commands': [{'argv': command, 'exit_code': completed.returncode}],
        'success_marker': 'AUAR_MARGIN_PASS',
        'log_sha256': sha(log),
        'hardware_source_sha256': before,
        'source_unchanged': source_unchanged,
        'baseline_checkpoint_unchanged': checkpoint_unchanged,
        'baseline': baseline_record,
        'goals': {'setup_min_ns': args.setup_min_ns, 'hold_min_ns': args.hold_min_ns},
        'metrics': metrics,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'board_accessed': False
    }
    save(out / 'implement.receipt.json', result)
    print('margin_refinement', result['status'], out / 'implement.receipt.json', flush=True)
    if not qualified:
        raise RuntimeError('margin refinement did not qualify; inspect the new output directory')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('ERROR', exc, file=sys.stderr)
        sys.exit(1)

