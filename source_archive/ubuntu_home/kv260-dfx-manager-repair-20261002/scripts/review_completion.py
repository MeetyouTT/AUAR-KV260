#!/usr/bin/env python3
"""Verify the collected evidence without executing another board operation."""
import datetime
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence'
OLD = Path('/home/ghmd/kv260-m3-boardtest-20261002/evidence/20261003T021012Z')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def pointer(name):
    return Path((EVIDENCE / name).read_text().strip())


def write_new(path, data):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    original = pointer('BOARD_VALIDATION_RUN')
    continuation = pointer('BOARD_CONTINUATION_RUN')
    preflight = pointer('BOARD_PREFLIGHT_RUN')
    audit = pointer('BOARD_FSTAB_AUDIT_RUN')
    final = read_json(continuation / 'controller.result.json')
    assert final['passed'] and final['original_baseline_restored']
    assert final['successful_commands'] == 17
    first = read_json(original / 'controller.result.json')
    assert not first['passed']
    assert '06-start-candidate' in first['error']

    ledger = []
    for run in (preflight, original, continuation, audit):
        for result in sorted(run.glob('*.results.jsonl')):
            phase = result.name.removesuffix('.results.jsonl') if hasattr(
                str, 'removesuffix') else result.name[:-len('.results.jsonl')]
            records = [json.loads(s) for s in result.read_text().splitlines()]
            assert records[0]['type'] == 'connection' and records[0]['ready']
            commands = [r for r in records if r.get('type') == 'command']
            manifest = read_json(run / (phase + '.commands.json'))
            assert [c['command'] for c in commands] == [
                c['command'] for c in manifest]
            assert [c['id'] for c in commands] == [c['id'] for c in manifest]
            for row in commands:
                output = run / (phase + '.' + row['id'] + '.output')
                assert row['complete'] and sha(output) == row['integrity_sha256']
                expected_failure = run == original and phase == '06-start-candidate'
                assert row['exit_code'] == (1 if expected_failure else 0)
                ledger.append({
                    'run': str(run.relative_to(ROOT)),
                    'phase': phase,
                    'id': row['id'],
                    'exit_code': row['exit_code'],
                    'complete': row['complete'],
                    'output': str(output.relative_to(ROOT)),
                    'sha256': sha(output),
                    'started_utc': row['started_utc'],
                    'finished_utc': row['finished_utc']
                })
    succeeded = sum(row['exit_code'] == 0 for row in ledger)
    failed = sum(row['exit_code'] != 0 for row in ledger)
    assert succeeded == 24 and failed == 1
    write_new(EVIDENCE / 'board_command_ledger.json', {
        'successful_commands': succeeded, 'failed_commands': failed,
        'all_outputs_complete_and_hash_verified': True,
        'transfer_counted_separately': first['transfer'],
        'commands': ledger
    })

    tree = read_json(OLD / 'dfx-mgr-tree.json')
    assert not tree['truncated']
    blobs = [r for r in tree['tree'] if r['type'] == 'blob']
    assert len(blobs) == 139
    baseline = ROOT / 'sources/dfx-mgr'
    patched = ROOT / 'sources/dfx-mgr-patched'
    for blob in blobs:
        data = (baseline / blob['path']).read_bytes()
        actual = hashlib.sha1(
            b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual == blob['sha']
    paths = {p.relative_to(baseline) for p in baseline.rglob('*') if p.is_file()}
    assert paths == {p.relative_to(patched) for p in patched.rglob('*') if p.is_file()}
    changed = sorted(str(p) for p in paths if sha(baseline / p) != sha(patched / p))
    assert changed == ['src/daemon_helper.c']
    diff = ''.join(difflib.unified_diff(
        (baseline / changed[0]).read_text().splitlines(keepends=True),
        (patched / changed[0]).read_text().splitlines(keepends=True),
        fromfile='a/' + changed[0], tofile='b/' + changed[0]))
    assert diff == (ROOT / 'artifacts/watch-dedup.patch').read_text()
    source_review = {
        'fixed_commit': 'bc06691eb35d7f0acb7c2508b6d050d77b0264a0',
        'baseline_git_blobs_verified': len(blobs),
        'changed_files': changed,
        'patch_matches_actual_source_diff': True,
        'patch_sha256': sha(ROOT / 'artifacts/watch-dedup.patch'),
        'baseline_helper_sha256': sha(baseline / changed[0]),
        'patched_helper_sha256': sha(patched / changed[0])
    }
    write_new(EVIDENCE / 'source_final_review.json', source_review)

    host = read_json(EVIDENCE / 'host_validation_summary.json')
    assert host['host_tests_passed']
    host_status = read_json(EVIDENCE / '20261003T035825.969132Z-host-tests/status.json')
    for row in host_status['commands']:
        assert row['exit_code'] == 0 and sha(ROOT / row['log']) == row['sha256']
    runtime_path = EVIDENCE / '20261003T040248.123957Z-runtime-review/status.json'
    runtime = read_json(runtime_path)
    assert runtime['passed'] and runtime['client_text_unchanged']
    for row in runtime['commands']:
        assert row['exit_code'] == 0 and sha(ROOT / row['log']) == row['sha256']
    for row in runtime['binaries']:
        assert sha(ROOT / row['path']) == row['sha256']
        assert not row['unresolved_strong_imports']
        assert row['build_rpath_removed'] and row['original_image_loader_list_passed']
    for run in ('20261003T035120.403885Z-baseline', '20261003T035243.033181Z-patched'):
        status = read_json(EVIDENCE / run / 'status.json')
        assert status['passed']
        for row in status['commands']:
            assert row['exit_code'] == 0 and sha(ROOT / row['log']) == row['sha256']
        for name, row in status['artifacts'].items():
            assert sha(ROOT / 'artifacts' / status['phase'] / name) == row['sha256']
    for row in read_json(EVIDENCE / 'source_acquisition.json')['sources']:
        assert sha(row['archive']) == row['archive_sha256']
    for row in read_json(EVIDENCE / 'build_inputs.json')['dependencies']:
        assert sha(ROOT / row['staged']) == row['sha256']
    candidate = next(r for r in runtime['binaries'] if r['phase'] == 'patched'
                     and Path(r['path']).name == 'dfx-mgrd')
    assert sha(ROOT / 'bundle-v2/kv260-dfx-watch-candidate/dfx-mgrd') == candidate['sha256']
    assert sha(ROOT / 'bundle-v2/kv260-dfx-watch-candidate.tar.gz') == first['transfer']['expected_sha256']

    log = continuation / '18-candidate-log.log.output'
    assert log.stat().st_size == final['final']['candidate_log_bytes']
    assert sha(log) == final['final']['candidate_log_sha256']
    diagnostic_terms = ('ERROR:', 'no room to add more watch',
                        'no room to add more watch to the base')
    counts = {term: log.read_text().count(term) for term in diagnostic_terms}
    assert not any(counts.values())

    raw_audit = (audit / '21-fstab-audit.configuration.output').read_text()
    live = json.loads(re.search(r'^FSTAB_AUDIT (.*)$', raw_audit, re.M)[1])
    assert live['original_files'] == final['final']['original_files']
    assert live['temporary_override_absent'] and live['test_directory_absent']
    image_fstab = audit / 'image-fstab-confirmed'
    assert not image_fstab.exists()
    argv = ['/sbin/debugfs', '-R', 'dump /etc/fstab ' + str(image_fstab),
            '/home/ghmd/kv260-dpu41-control-20261001/evidence/baseline-rootfs.ext4']
    dumped = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert dumped.returncode == 0 and image_fstab.is_file()
    assert sha(image_fstab) == live['fstab_sha256']
    assert image_fstab.read_text() == live['fstab']
    boot_entries = [s for s in live['fstab'].splitlines()
                    if s and not s.startswith('#') and len(s.split()) >= 2
                    and s.split()[1] == '/boot']
    assert len(boot_entries) == 2
    assert len(live['boot_mountinfo']) == 1 and len(live['boot_proc_mounts']) == 1
    assert 'ActiveState=active' in live['boot_unit'] and 'Result=success' in live['boot_unit']
    fstab_review = {
        'actual_problem': 'Two active /etc/fstab entries target /boot',
        'boot_entries': boot_entries, 'board_fstab_sha256': live['fstab_sha256'],
        'matches_preexisting_baseline_rootfs': True,
        'baseline_extraction': {'argv': argv, 'exit_code': dumped.returncode,
                                'stdout': dumped.stdout, 'stderr': dumped.stderr},
        'actual_boot_mounts': live['boot_proc_mounts'], 'boot_unit': live['boot_unit'],
        'board_configuration_modified': False,
        'scope': 'Confirmed preexisting baseline configuration; does not attribute the entries to the vendor image or their author.'
    }
    write_new(audit / 'review.json', fstab_review)

    epoch = float(read_json(preflight / '01-readonly.identity_manager.output')['uptime'].split()[0])
    kernel_lines = {}
    for row in ledger:
        if '18-candidate-log' in row['phase']:
            continue
        for line in (ROOT / row['output']).read_text().splitlines():
            match = re.match(r'^\[\s*([0-9]+[.][0-9]+)\] (.*)', line)
            if match and float(match[1]) >= epoch:
                kernel_lines[float(match[1])] = line
    unique = [kernel_lines[t] for t in sorted(kernel_lines)]
    refs = [s for s in unique if 'expected refcount' in s]
    assert len(refs) == 1 and 'expected refcount 1 instead of 2' in refs[0]
    assert '/axi/zyxclmm_drm' in refs[0]
    fstab_failures = [s for s in unique if 'systemd-fstab-generator' in s and 'Failed to create' in s]
    property_warnings = [s for s in unique if 'OF: overlay: WARNING: memory leak will occur' in s]
    sysv_warnings = [s for s in unique if 'systemd-sysv-generator' in s and 'lacks a native systemd unit' in s]
    recognized = set(refs + fstab_failures + property_warnings + sysv_warnings)
    other = [s for s in unique if re.search(r'\b(ERROR|WARNING|BUG|Oops|panic|segfault|Failed|failure)\b', s)
             and s not in recognized]
    assert not other, 'Inspect additional diagnostics rather than silently discarding them'
    kernel_review = {
        'scope': 'Deduplicated collected kernel lines since the read-only preflight, using board uptime',
        'preflight_uptime': epoch,
        'known_original_driver_exit_refcount_errors': refs,
        'new_target_refcount_errors_with_repaired_driver': 0,
        'fstab_generator_failures': fstab_failures,
        'overlay_property_warning_count': len(property_warnings),
        'overlay_property_warnings': property_warnings,
        'sysv_compatibility_warning_count': len(sysv_warnings),
        'sysv_compatibility_warnings': sysv_warnings,
        'other_error_or_warning_lines': other,
        'all_deduplicated_lines': unique
    }
    write_new(EVIDENCE / 'kernel_diagnostics_review.json', kernel_review)

    output = {
        'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'result': 'Candidate passed finite host and board validation; original baseline restored',
        'host_tests_passed': True, 'board_verified': True,
        'permanent_installation': False, 'original_baseline_restored': True,
        'successful_board_commands': succeeded, 'failed_board_commands': failed,
        'known_failed_probe': {
            'phase': '06-start-candidate',
            'reason': 'Test readiness probe incorrectly used SOCK_STREAM for the vendor SOCK_SEQPACKET service',
            'fixed_probe': '20-ready-check; continued from the observed active candidate without retrying startup',
            'production_candidate_binary_changed_for_probe_fix': False
        },
        'source_review': source_review,
        'host_results': host['results'],
        'sanitizers': host['sanitizers'],
        'runtime_review': str(runtime_path.relative_to(ROOT)),
        'candidate': candidate,
        'query_stress': final['query_stress'],
        'directory_stress': final['directory_stress'],
        'official_cycles': final['official_cycles'],
        'functional': final['functional'],
        'candidate_log': {'path': str(log.relative_to(ROOT)), 'bytes': log.stat().st_size,
                          'sha256': sha(log), 'diagnostic_counts': counts,
                          'collection_after_graceful_SIGINT_flush': True},
        'known_original_driver_exit_refcount_errors': refs,
        'new_target_refcount_errors_with_repaired_driver': 0,
        'overlay_property_warning_count': len(property_warnings),
        'fstab_review': str((audit / 'review.json').relative_to(ROOT)),
        'final': final['final'],
        'final_readonly_confirmation': {
            k: live[k] for k in ('boot_id', 'uptime', 'active', 'driver', 'manager_exe',
                                'temporary_override_absent', 'test_directory_absent')
        },
        'limitations': [
            'No permanent candidate installation or automatic startup of repaired binaries',
            'Original manager and original ZOCL defects remain in the restored originals',
            'No new FPS benchmark, M3 register access, PWM, actuator or sustained memory-leak measurement',
            'Watch writer mutex validation is not a proof of all daemon shared-state thread safety',
            'Existing overlay property warnings, DRC and timing limitations remain',
            'Duplicate baseline /boot fstab entries recorded and not changed'
        ]
    }
    write_new(EVIDENCE / 'validation_summary.json', output)
    print(json.dumps({
        'board_verified': True, 'baseline_restored': True,
        'successful_board_commands': succeeded, 'failed_probe_commands': failed,
        'candidate_error_count': counts['ERROR:'],
        'baseline_fstab_duplicate_confirmed': True,
        'overlay_property_warning_count': len(property_warnings)
    }))


if __name__ == '__main__':
    main()
