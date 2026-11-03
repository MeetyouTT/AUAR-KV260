#!/usr/bin/env python3
"""Review captured evidence only; never connect to or change the board."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    run = Path(sys.argv[1]).resolve()
    preflight = root / 'evidence/board_preflight'
    records = [json.loads(line) for line in
               (preflight / '01-readonly.results.jsonl').read_text().splitlines()]
    commands = [row for row in records if row.get('type') == 'command']
    manifest = json.loads((preflight / '01-readonly.commands.json').read_text())
    assert any(row.get('type') == 'connection' and row.get('ready') for row in records)
    assert [row['id'] for row in commands] == [row['id'] for row in manifest]
    assert [row['command'] for row in commands] == [row['command'] for row in manifest]
    for row in commands:
        assert row['complete'] and row['exit_code'] == 0
        assert sha(preflight / ('01-readonly.' + row['id'] + '.output')) == row['integrity_sha256']

    live_config = preflight / '01-readonly.kernel_config.output'
    original_config = root / 'evidence/image_files/kernel.config'
    assert live_config.read_bytes() == original_config.read_bytes()
    original_runtime = (preflight / '01-readonly.identity_runtime.output').read_text()
    board_hashes = {}
    for line in original_runtime.splitlines():
        if line.startswith('{"path":'):
            item = json.loads(line)
            board_hashes[item['path']] = item['sha256']
    runtime_paths = [
        '/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko',
        '/usr/lib/libxrt_core.so.2.14.0', '/usr/bin/dfx-mgrd', '/usr/lib/libdfx.so.1.0']
    runtime = []
    for path in runtime_paths:
        image_file = root / 'evidence/image_files' / Path(path).name
        assert board_hashes[path] == sha(image_file)
        runtime.append({'board_path': path, 'sha256': board_hashes[path], 'matches_image': True})

    controller = json.loads((run / 'cycle_controller.result.json').read_text())
    assert controller['passed'] and controller['completed_phases'] == controller['phases']
    assert 'error' not in controller
    assert controller['runner_sha256'] == sha(root / 'scripts/run_validation_and_recovery.py')
    assert controller['collector_sha256'] == sha(run / 'collect_serial.py')
    summary = json.loads((run / 'board_validation_summary.json').read_text())
    assert summary['board_verified'] and summary['baseline_hashes_unchanged']

    warning_prefix = 'OF: overlay: WARNING: memory leak will occur if overlay removed, property:'
    initial_kernel = (preflight / '01-readonly.kernel_before.output').read_text()
    observed_warnings = {line for line in initial_kernel.splitlines() if warning_prefix in line}
    initial_warnings = len(observed_warnings)
    for output in run.glob('*.output'):
        text = output.read_text()
        if 'AFTER_DMESG_BEGIN\n' in text:
            kernel = text.split('AFTER_DMESG_BEGIN\n', 1)[1].split('AFTER_DMESG_END', 1)[0]
            observed_warnings.update(line for line in kernel.splitlines() if warning_prefix in line)
    load_warnings = {}
    for phase in ['c1-load-official', 'c2-load-official', 'c3-load-official', 'r3-restore-official-app']:
        review = json.loads((run / (phase + '.review.json')).read_text())
        load_warnings[phase] = sum(len(row['property_warnings']) for row in review['commands'])

    final_kernel = (run / 'r3-restore-official-app.restore-official-app.output').read_text()
    final_kernel = final_kernel.split('AFTER_DMESG_BEGIN\n', 1)[1].split('AFTER_DMESG_END', 1)[0]
    timed = [(float(match[1]), line) for line in final_kernel.splitlines()
             for match in [re.match(r'^\[\s*([0-9.]+)\]', line)] if match]
    epoch = json.loads((run / '09-unload-original-module.review.json').read_text())['commands'][0]['uptime_after']
    last_cycle = summary['cycles'][-1]['uptime_after_snapshot_start']
    assert min(t for t, _ in timed) <= epoch
    assert max(t for t, _ in timed) >= last_cycle
    post_repair = [line for t, line in timed if t >= epoch and 'expected refcount' in line]
    assert not post_repair

    result = {
        'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'passed': True,
        'preflight_successful_commands': len(commands),
        'main_successful_commands': summary['successful_commands'],
        'kernel_config': {'bytes': live_config.stat().st_size, 'sha256': sha(live_config), 'exact_match': True},
        'runtime_matches_original_image': runtime,
        'controller_final_result_passed': True,
        'controller_finished_utc': controller['finished_utc'],
        'property_warnings': {
            'initial_snapshot': initial_warnings, 'new_per_load': load_warnings,
            'unique_observed_lines_across_snapshots': len(observed_warnings),
            'final_snapshot_retained_lines': sum(warning_prefix in line for line in final_kernel.splitlines()),
            'note': 'Snapshots of the kernel ring buffer overlap; unique lines include their uptime timestamps.'},
        'delayed_refcount_check': {
            'epoch_after_original_module_unload': epoch,
            'final_retained_dmesg_first_uptime': min(t for t, _ in timed),
            'final_retained_dmesg_last_uptime': max(t for t, _ in timed),
            'new_refcount_errors_after_epoch': len(post_repair)},
        'note': 'Progress/checkpoint files are intermediate snapshots; the controller result and final summary are authoritative.'}
    destination = run / 'preflight_and_diagnostics_review.json'
    assert not destination.exists(), 'Refusing to overwrite review evidence'
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
