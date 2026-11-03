#!/usr/bin/env python3
"""Independently re-read every exported file and evaluate actual board evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BOARD_ROOT = Path('/home/root/kv260-dfx-state-boardtest-20261004')
NEW_SHA = '369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd'
OLD_SHA = 'db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c'
BOOT = 'a7733edd-db41-4527-b8fb-cefdcbfe7b3a'
TOP5 = [(258, '0.949879'), (270, '0.00931229'), (259, '0.00821807'),
        (257, '0.00498451'), (279, '0.00388194')]
CLASSIFY = '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification'
MODEL = '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel'
IMAGE = '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    archive = Path(sys.argv[1]).resolve()
    expected = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'acceptance'
    if mode not in ('acceptance', 'installed', 'postboot'):
        raise SystemExit('mode must be acceptance, installed or postboot')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'reviews' / (stamp + '-' + mode)
    out.mkdir(parents=True, exist_ok=False)
    checks = {}
    detail = {'archive': str(archive), 'mode': mode, 'created_utc': stamp, 'checks': checks, 'passed': False}

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise RuntimeError('Evidence check failed: ' + name)

    def write_json(path, data):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

    try:
        check('archive_sha256', sha(archive.read_bytes()) == expected)
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            check('safe_regular_members', all(m.isfile() and not Path(m.name).is_absolute() and
                  '..' not in Path(m.name).parts for m in members))
            check('unique_member_names', len(set(m.name for m in members)) == len(members))
            files = {m.name: tar.extractfile(m).read() for m in members}
        manifest = json.loads(files['EXPORT_MANIFEST.json'])
        check('manifest_covers_all_files', set(files) == set(manifest) | {'EXPORT_MANIFEST.json'})
        for name, item in manifest.items():
            check('member_' + name, len(files[name]) == item['bytes'] and sha(files[name]) == item['sha256'])
        detail['verified_exported_files'] = len(manifest)
        extracted = out / 'board'
        extracted.mkdir()
        for name, data in files.items():
            p = extracted / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        def obj(name):
            return json.loads(files[name])

        def phase(name):
            status = obj('phase-' + name + '.json')
            check(name + '_complete', status['complete'] and status['error'] is None)
            check(name + '_all_checks', all(status['checks'].values()) and bool(status['checks']))
            folder = Path(status['evidence']).relative_to(BOARD_ROOT).as_posix()
            check(name + '_matches_immutable_summary', obj(folder + '/summary.json') == status)
            records = [json.loads(line) for line in files[folder + '/commands.jsonl'].decode().splitlines()]
            check(name + '_command_count', len(records) == status['commands'])
            for command in records:
                prefix = folder + '/' + command['id']
                check(name + '_stdout_' + command['id'], sha(files[prefix + '.stdout']) == command['stdout_sha256'])
                check(name + '_stderr_' + command['id'], sha(files[prefix + '.stderr']) == command['stderr_sha256'])
                if command['rc'] != 0:
                    stderr = files[prefix + '.stderr'].decode()
                    check(name + '_only_bounded_startup_probe_' + command['id'], command['rc'] == 255 and
                          'startup-list-probe' in command['id'] and 'connect(/tmp/dfx-mgrd.socket)' in stderr and
                          ('Connection refused' in stderr or 'No such file or directory' in stderr))
            return status, folder, records

        phases = {}
        required = ['backup', 'unpack', 'ready', 'stress', 'recover-missing-xclbin-probe', 'active-move', 'cycles', 'restore']
        if mode in ('installed', 'postboot'):
            required += ['persist']
        if mode == 'postboot':
            required += ['prepare-coldboot', 'postboot', 'coldboot-order']
        for name in required:
            phases[name] = phase(name)
        detail['accepted_phases'] = required

        copies = {'validate.py': 'validate-v1.py', 'validate_v2.py': 'validate-v2.py',
                  'validate_v3.py': 'validate-v3.py', 'validate_v4.py': 'validate-v4.py', 'validate_v5.py': 'validate.py'}
        for remote, local in copies.items():
            check('validator_provenance_' + remote, sha(files['board/' + remote]) == sha((ROOT / 'board' / local).read_bytes()))
        check('recovery_old_binary', obj('recovery.json')['manager_sha256'] == OLD_SHA and
              sha(files['backup/usr/local/lib/kv260-runtime-repair/dfx-mgrd']) == OLD_SHA)
        unpack = obj(phases['unpack'][1] + '/unpacked.json')
        check('same_candidate_binary', unpack['candidate_sha256'] == NEW_SHA and unpack['regular_members'] == 154 and
              unpack['client_deployed'] is False)

        baseline = obj('candidate-baseline.json')
        directory = obj(phases['stress'][1] + '/directory-cycles.json')
        check('100_multilevel_directory_cycles', len(directory) == 100 and all(
              d['children'] == 3 and d['grandchildren'] == 6 and d['added_watch_count'] == 16 and
              d['removed_watch_count'] == 6 for d in directory))
        list_records = [r for r in phases['stress'][2] if 'parallel-list-' in r['id']]
        check('1000_actual_concurrent_list_calls', len(list_records) == 1000 and all(r['rc'] == 0 for r in list_records))
        latency = obj(phases['stress'][1] + '/query-latency.json')
        check('1000_recorded_latencies', latency['count'] == 1000 and len(latency['all_seconds']) == 1000)
        detail['query_latency_seconds'] = {k: v for k, v in latency.items() if k != 'all_seconds'}
        for name in ['stress', 'cycles']:
            state = obj(phases[name][1] + '/final-state.json')
            check(name + '_watch_fd_pid_stable', state['watch_count'] == 5 and state['inotify_fd_count'] == 1 and
                  state['fd_count'] == baseline['fd_count'] and state['pid'] == baseline['pid'])
        before = obj(phases['active-move'][1] + '/loaded-state.json')
        disappeared = obj(phases['active-move'][1] + '/disappeared-state.json')
        check('real_loaded_hardware_survived_directory_move', before['overlays'] == disappeared['overlays'] ==
              ['kv260-sv-active_image_1'] and before['render_nodes'] == disappeared['render_nodes'] == ['renderD128'] and
              disappeared['watch_count'] == 5)
        cycle_unloads = [r for r in phases['cycles'][2] if re.search(r'cycle-\d\d-unload$', r['id'])]
        cycle_loads = [r for r in phases['cycles'][2] if re.search(r'cycle-\d\d-load$', r['id'])]
        check('10_real_official_load_unload_cycles', len(cycle_unloads) == len(cycle_loads) == 10 and
              all(r['rc'] == 0 for r in cycle_loads + cycle_unloads))

        reference_query = None
        functional = []
        for name in required:
            for r in phases[name][2]:
                prefix = phases[name][1] + '/' + r['id']
                if 'xdputil' in r['argv'] and 'query' in r['argv']:
                    q = json.loads(files[prefix + '.stdout'])
                    normalized = {k: v for k, v in q.items() if k != 'kernels'}
                    normalized['kernels'] = [{k: v for k, v in kernel.items() if k != 'cu_handle'} for kernel in q['kernels']]
                    if reference_query is None:
                        reference_query = normalized
                    check('same_query_' + name + '_' + r['id'], r['rc'] == 0 and normalized == reference_query)
                if CLASSIFY in r['argv']:
                    check('original_model_image_' + name + '_' + r['id'], r['argv'][-2:] == [MODEL, IMAGE])
                    text = (files[prefix + '.stdout'] + files[prefix + '.stderr']).decode()
                    top5 = [(int(a), b) for a, b in re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)', text)]
                    check('actual_top5_' + name + '_' + r['id'], r['rc'] == 0 and top5 == TOP5)
                    functional.append({'phase': name, 'command': r['id'], 'top5': top5, 'argv': r['argv']})
        detail['actual_classifications'] = functional
        detail['classification_count'] = len(functional)

        kernel_before = next(files[phases['backup'][1] + '/' + r['id'] + '.stdout'].decode()
                             for r in phases['backup'][2] if r['argv'] == ['dmesg'])
        kernel_after = next(files[phases['cycles'][1] + '/' + r['id'] + '.stdout'].decode()
                            for r in phases['cycles'][2] if r['argv'] == ['dmesg'])
        timestamps = [float(v) for v in re.findall(r'^\[\s*([\d.]+)\]', kernel_before, re.M)]
        cutoff = max(timestamps)
        new_lines = [line for line in kernel_after.splitlines() if
                     (m := re.match(r'^\[\s*([\d.]+)\]', line)) and float(m[1]) > cutoff]
        severe = [line for line in new_lines if re.search(
                  r'\bBUG:|\bOops:|Kernel panic|use.after.free|KASAN:|Call trace:|Unable to handle kernel|'
                  r'blocked for more than|soft lockup|hard LOCKUP|I/O error|EXT4-fs error|'
                  r'FAT-fs.*(?:corrupt|not properly unmounted)|timed out|timeout', line, re.I)]
        warnings = [line for line in new_lines if re.search(r'warn|error|fail|ret.?=.?-13|not found|skip', line, re.I)]
        kernel_review = {'baseline_last_monotonic_seconds': cutoff, 'new_line_count': len(new_lines),
                         'severe_pattern_matches': severe, 'warning_candidates': warnings,
                         'scope': 'Keyword review of this acceptance time window; does not prove absence of all kernel defects.'}
        write_json(out / 'KERNEL_REVIEW.json', kernel_review)
        check('no_new_severe_pattern_in_acceptance_window', not severe)
        detail['kernel_warning_candidates'] = len(warnings)

        failures = []
        for filename, data in files.items():
            if filename.startswith('evidence/') and filename.endswith('/summary.json'):
                status = json.loads(data)
                if not status['complete']:
                    failures.append({'file': filename, 'phase': status['phase'], 'error': status['error']})
        detail['preserved_incomplete_attempts'] = failures
        check('four_earlier_incomplete_attempts_preserved', len(failures) == 4)
        restored = obj(phases['restore'][1] + '/restored-state.json')
        check('restoration_watch_baseline', restored['watch_count'] == 5)
        detail['candidate_sha256'] = NEW_SHA
        detail['boot_id'] = BOOT
        detail['cold_boot_verified'] = False
        detail['installed'] = False
        if mode in ('installed', 'postboot'):
            installed = obj('persistent-install.json')
            check('persistent_binary_hash', installed['candidate_sha256'] == NEW_SHA)
            check('persistent_config_digest', installed['sha256'] == sha(installed['content'].encode()))
            check('persistent_config_exact_path', installed['path'] ==
                  '/etc/systemd/system/dfx-mgr.service.d/20-kv260-dfx-state-repaired.conf')
            state = obj(phases['persist'][1] + '/persistent-state.json')
            check('persistent_watch_baseline', state['watch_count'] == 5 and state['inotify_fd_count'] == 1)
            detail['installed'] = True
            detail['persistent_pid'] = state['pid']
            detail['persistent_dropin_sha256'] = installed['sha256']
        if mode == 'postboot':
            detail['boot_id'] = phases['postboot'][0]['boot_id']
            check('new_boot_verified', detail['boot_id'] != BOOT)
            check('coldboot_phase_boot_ids', phases['prepare-coldboot'][0]['boot_id'] == BOOT and
                  phases['coldboot-order'][0]['boot_id'] == detail['boot_id'])
            state = obj(phases['postboot'][1] + '/postboot-state.json')
            check('postboot_hardware_and_watch_state', state['watch_count'] == 5 and
                  state['inotify_fd_count'] == 1 and state['fd_count'] == baseline['fd_count'] and
                  state['overlays'] == ['kv260-benchmark-b4096_image_1'] and
                  state['render_nodes'] == ['renderD128'])
            detail['postboot_pid'] = state['pid']
            ordering = obj(phases['coldboot-order'][1] + '/ordering.json')
            loader = ordering['kv260-repaired-zocl.service']
            mgr = ordering['dfx-mgr.service']
            check('actual_driver_completed_before_manager_exec',
                  0 < int(loader['ExecMainExitTimestampMonotonic']) < int(mgr['ExecMainStartTimestampMonotonic']))
            check('postboot_manager_enabled_and_running', mgr['UnitFileState'] == 'enabled' and
                  mgr['ActiveState'] == 'active' and mgr['SubState'] == 'running' and
                  int(mgr['MainPID']) == state['pid'] and mgr['Result'] == 'success')
            check('postboot_loader_required_and_ordered', 'kv260-repaired-zocl.service' in mgr['Requires'].split()
                  and 'kv260-repaired-zocl.service' in mgr['After'].split() and
                  loader['Result'] == 'success' and loader['ExecMainStatus'] == '0')
            detail['driver_finished_monotonic_seconds'] = int(loader['ExecMainExitTimestampMonotonic']) / 1000000
            detail['manager_started_monotonic_seconds'] = int(mgr['ExecMainStartTimestampMonotonic']) / 1000000

            def command_output(phase_name, name):
                records = phases[phase_name][2]
                record = next(r for r in records if r['id'].endswith('-' + name))
                return files[phases[phase_name][1] + '/' + record['id'] + '.stdout']

            runtime_hashes = {line.split('  ', 1)[1]: line.split('  ', 1)[0] for line in
                              command_output('coldboot-order', 'preserved-runtime-hashes').decode().splitlines()}
            recovery_hashes = obj('recovery.json')['backup_hashes']
            check('coldboot_preserved_runtime_hashes', len(runtime_hashes) == 4 and
                  all(digest == recovery_hashes[path] for path, digest in runtime_hashes.items()))
            fstab = command_output('coldboot-order', 'fstab')
            check('coldboot_fstab_digest', sha(fstab) == recovery_hashes['/etc/fstab'])
            fstab_entries = [line.split() for line in fstab.decode().splitlines() if line.strip() and
                             not line.lstrip().startswith('#')]
            check('single_fstab_boot_entry', [f for f in fstab_entries if f[1] == '/boot'] ==
                  [['LABEL=boot', '/boot', 'vfat', 'defaults', '0', '2']])
            check('coldboot_expected_root_mount', command_output('coldboot-order', 'root-mount').decode().split() ==
                  ['/dev/mmcblk1p2', 'ext4', '/'])
            check('coldboot_expected_boot_mount', command_output('coldboot-order', 'boot-mount').decode().split() ==
                  ['/dev/mmcblk1p1', 'vfat', '/boot'])

            confirmation_bytes = (ROOT / 'POWER_CYCLE_CONFIRMATION.json').read_bytes()
            confirmation = json.loads(confirmation_bytes)
            check('physical_power_cycle_user_confirmation', confirmation['physical_cycle_reported_by_user'] is True
                  and confirmation['user_message'] == '已重新上电' and confirmation['boot_id_before'] == BOOT
                  and confirmation['boot_id_after'] == detail['boot_id'])
            proof_hashes = {'POWER_CYCLE_CONFIRMATION.json': sha(confirmation_bytes)}

            def host_proof(key):
                relative = Path(confirmation[key])
                check('safe_host_proof_path_' + key, not relative.is_absolute() and '..' not in relative.parts)
                data = (ROOT / relative).read_bytes()
                proof_hashes[relative.as_posix()] = sha(data)
                return data

            shutdown = json.loads(host_proof('shutdown_status'))
            shutdown_raw = host_proof('shutdown_serial')
            poweroff = next(r for r in shutdown['results'] if r['id'] == 'clean-poweroff')
            check('clean_shutdown_before_physical_cycle', shutdown['complete'] and
                  poweroff['exit_code'] == 0 and poweroff['powerdown_confirmed'] and
                  poweroff['command'] == 'systemctl --no-block poweroff' and
                  poweroff['console_echo_restored_before_shutdown'] and b'reboot: Power down' in shutdown_raw)
            observation = json.loads(host_proof('boot_observation_status'))
            boot_raw = host_proof('boot_observation_serial')
            check('passive_boot_serial_digest', len(boot_raw) == observation['serial_bytes'] and
                  sha(boot_raw) == observation['serial_sha256'])
            check('passive_fresh_boot_and_root_login', observation['complete'] and observation['read_only'] and
                  observation['uart_bytes_sent'] == 0 and observation['fresh_boot_marker_seen'] and
                  observation['root_prompt_seen'] and b'U-Boot' in boot_raw and
                  b'Linux version 5.15.36-xilinx-v2022.2' in boot_raw and
                  re.search(rb'root@[^\r\n]+:[^\r\n]*# ', boot_raw) is not None)
            uart_status = json.loads(host_proof('postboot_uart_status'))
            check('postboot_uart_complete_and_echo_restored', uart_status['complete'] and
                  uart_status['console_echo_restored'] and all(r['exit_code'] == 0 for r in uart_status['results']))
            observation_start = datetime.datetime.strptime(observation['started_utc'], '%Y%m%dT%H%M%S.%fZ').replace(
                tzinfo=datetime.timezone.utc)
            check('shutdown_then_observation_then_postboot',
                  datetime.datetime.fromisoformat(poweroff['finished_utc']) < observation_start <
                  datetime.datetime.fromisoformat(observation['finished_utc']) <
                  datetime.datetime.fromisoformat(uart_status['started_utc']))
            boot_kernel = command_output('postboot', 'boot-kernel').decode()
            boot_journal = command_output('postboot', 'boot-journal').decode()
            critical = [line for line in boot_kernel.splitlines() if re.search(
                        r'\bBUG:|\bOops:|Kernel panic|use.after.free|KASAN:|Call trace:|Unable to handle kernel|'
                        r'blocked for more than|soft lockup|hard LOCKUP|I/O error|EXT4-fs error|'
                        r'FAT-fs.*(?:corrupt|not properly unmounted)', line, re.I)]
            boot_warnings = [line for line in boot_kernel.splitlines() if re.search(
                             r'warn|error|fail|ret.?=.?-13|not found|skip', line, re.I)]
            check('coldboot_no_critical_kernel_pattern', not critical)
            check('coldboot_no_duplicate_mount_entry', re.search(
                  r'(?:found )?duplicate (?:entry|entries).*boot', boot_journal, re.I) is None)
            failed_units = command_output('postboot', 'failed-units').decode()
            write_json(out / 'COLD_BOOT_VERIFICATION.json', {
                'passed': True, 'user_confirmation': confirmation, 'host_proof_sha256': proof_hashes,
                'boot_id_before': BOOT, 'boot_id_after': detail['boot_id'], 'pid': state['pid'],
                'driver_finished_monotonic_seconds': detail['driver_finished_monotonic_seconds'],
                'manager_started_monotonic_seconds': detail['manager_started_monotonic_seconds'],
                'critical_kernel_pattern_matches': critical, 'kernel_warning_candidates': boot_warnings,
                'failed_units_output': failed_units,
                'scope': 'One user-confirmed physical power cycle. Power rail/off duration not instrumented; '
                         'keyword review does not prove absence of all kernel defects.'})
            detail['cold_boot_verified'] = True
            detail['coldboot_kernel_warning_candidates'] = len(boot_warnings)
            detail['reviewer_sha256'] = sha(Path(__file__).read_bytes())
        detail['passed'] = True
        detail['extracted'] = str(extracted)
        if mode == 'acceptance':
            write_json(ROOT / 'acceptance-review.json', {'passed': True, 'candidate_sha256': NEW_SHA, 'boot_id': BOOT,
                       'archive_sha256': expected, 'review': str(out / 'review.json'),
                       'verified_files': len(manifest), 'accepted_phases': required})
    except Exception as exc:
        detail['error'] = '%s: %s' % (type(exc).__name__, exc)
    finally:
        write_json(out / 'review.json', detail)
        write_json(ROOT / 'CURRENT_REVIEW.json', {'review': str(out / 'review.json'), 'passed': detail['passed']})
    print(json.dumps({'passed': detail['passed'], 'review': str(out / 'review.json'),
                     'verified_files': detail.get('verified_exported_files'),
                     'classifications': detail.get('classification_count'), 'error': detail.get('error')}, ensure_ascii=False))
    raise SystemExit(0 if detail['passed'] else 1)


if __name__ == '__main__':
    main()
