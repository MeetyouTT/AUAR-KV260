#!/usr/bin/env python3
"""Re-read all NFS repair evidence; separate runtime and cold-boot results."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
UART_ROOT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004')
REMOTE = Path('/home/root/kv260-platform-warnings-20261004/nfs')
OLD_BOOT = '01ca88c1-93b6-414f-9646-774482d4b2f0'
TOP5 = [(258, '0.949879'), (270, '0.00931229'), (259, '0.00821807'),
        (257, '0.00498451'), (279, '0.00388194')]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    archive = Path(sys.argv[1]).resolve()
    expected = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'warm'
    assert mode in ('warm', 'postboot', 'user-coldboot')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'reviews' / (stamp + '-' + mode)
    out.mkdir(parents=True, exist_ok=False)
    result = {'archive': str(archive), 'archive_sha256': expected, 'mode': mode,
              'passed': False, 'cold_boot_verified': False, 'checks': {}}

    def check(name, value):
        result['checks'][name] = bool(value)
        if not value:
            raise RuntimeError('Check failed: ' + name)

    def save(path, obj):
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

    try:
        check('archive_sha256', sha(archive.read_bytes()) == expected)
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            check('safe_unique_regular_members', len({m.name for m in members}) == len(members)
                  and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members))
            files = {m.name: tar.extractfile(m).read() for m in members}
        manifest = json.loads(files['EXPORT_MANIFEST.json'])
        check('manifest_covers_all_members', set(files) == set(manifest) | {'EXPORT_MANIFEST.json'})
        for name, item in manifest.items():
            check('file_' + name, len(files[name]) == item['bytes'] and sha(files[name]) == item['sha256'])
        result['verified_files'] = len(manifest)
        board = out / 'board'
        board.mkdir()
        for name, data in files.items():
            p = board / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        controllers = {Path(name).name: sha(data) for name, data in files.items() if name.startswith('CONTROLLERS/')}
        check('all_three_controller_versions_preserved', set(controllers) ==
              {'nfs_repair_v1.py', 'nfs_repair_v2.py', 'nfs_repair_v3.py'})
        for name, digest in controllers.items():
            check('controller_provenance_' + name, sha((UART_ROOT / 'board' / name).read_bytes()) == digest)
        tree = ast.parse(files['CONTROLLERS/nfs_repair_v3.py'])
        content = next(ast.literal_eval(node.value) for node in tree.body
                       if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CONTENT' for t in node.targets))
        phases = {}
        required = ['backup', 'apply']
        if mode == 'postboot':
            required += ['prepare-coldboot', 'postboot']
        elif mode == 'user-coldboot':
            required += ['postboot']
        for phase in required:
            status = json.loads(files['phase-' + phase + '.json'])
            folder = Path(status['evidence']).relative_to(REMOTE).as_posix()
            check(phase + '_complete_and_checks', status['complete'] and status['error'] is None
                  and bool(status['checks']) and all(status['checks'].values()))
            check(phase + '_immutable_summary', json.loads(files[folder + '/summary.json']) == status)
            check(phase + '_verified_controller', status['controller_sha256'] in controllers.values())
            check(phase + '_driver_provenance', status['driver_sha256'] ==
                  sha((UART_ROOT / 'board/validate.py').read_bytes()))
            commands = [json.loads(line) for line in files[folder + '/commands.jsonl'].splitlines()]
            check(phase + '_command_count', len(commands) == status['commands'])
            for command in commands:
                prefix = folder + '/' + command['id']
                stdout, stderr = files[prefix + '.stdout'], files[prefix + '.stderr']
                check(phase + '_stdout_' + command['id'], sha(stdout) == command['stdout_sha256'])
                check(phase + '_stderr_' + command['id'], sha(stderr) == command['stderr_sha256'])
                check(phase + '_return_' + command['id'], command['rc'] == 0 or
                      (command['argv'] == ['findmnt', '-rn', '-t', 'nfs,nfs4', '-o', 'FSTYPE,TARGET'] and
                       command['rc'] == 1 and not stdout and not stderr))
            phases[phase] = (status, folder, commands)
        check('live_dropin_exact', files[phases['apply'][1] + '/installed-dropin.conf'].decode() == content)
        install = json.loads(files['installed.json'])
        check('live_dropin_sha256', sha(content.encode()) == install['configuration_sha256'])
        result['configuration_sha256'] = install['configuration_sha256']
        before = json.loads(files['recovery.json'])
        check('original_enable_links_preserved_for_rollback', len(before['enable_links']) == 2 and
              all(item['kind'] == 'symlink' for item in before['enable_links'].values()))
        for name, item in before['protected'].items():
            if item['kind'] == 'file':
                check('backup_original_' + name, sha(files['backup/' + name.lstrip('/')]) == item['sha256'])
        classifications = []
        for phase in ['apply'] + (['postboot'] if mode != 'warm' else []):
            status, folder, commands = phases[phase]
            observed = {'classification': 0, 'failed_units': 0, 'original_files': 0, 'dpu_query': 0, 'tpm_query': 0}
            states = json.loads(files[folder + '/unit-states.json'])
            mount = states['proc-fs-nfsd.mount']
            check(phase + '_unsupported_mount_actually_skipped', mount['ConditionResult'] == 'no' and
                  mount['ActiveState'] == 'inactive' and int(mount['ConditionTimestampMonotonic']) > 0)
            check(phase + '_server_startup_disabled', all(states[name]['UnitFileState'] == 'disabled'
                  and states[name]['ActiveState'] == 'inactive' for name in install['server_services_disabled']))
            check(phase + '_client_states_preserved', all(states[name].get(key) == before['states'][name].get(key)
                  for name in install['client_services_preserved'] for key in ['UnitFileState', 'ActiveState', 'SubState']))
            runtime = json.loads(files[folder + '/runtime-state.json'])
            check(phase + '_same_hardware_watch_state', runtime['watch_count'] == 5 and runtime['inotify_fd_count'] == 1
                  and runtime['overlays'] == before['watch_state']['overlays'] and runtime['render_nodes'] == before['watch_state']['render_nodes'])
            for command in commands:
                prefix = folder + '/' + command['id']
                stdout, stderr = files[prefix + '.stdout'], files[prefix + '.stderr']
                if 'classification/test_jpeg_classification' in command['argv'][0]:
                    observed['classification'] += 1
                    scores = [(int(a), b) for a, b in re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)', (stdout + stderr).decode())]
                    check(phase + '_original_image_model', command['argv'][-2:] ==
                          ['/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel', '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'])
                    check(phase + '_original_top5', scores == TOP5)
                    classifications.append({'phase': phase, 'scores': scores})
                if command['argv'] == ['systemctl', 'list-units', '--failed', '--no-legend', '--plain', '--no-pager']:
                    observed['failed_units'] += 1
                    check(phase + '_zero_failed_units', not stdout.strip())
                if command['argv'][:2] == ['sha256sum', '-c']:
                    observed['original_files'] += 1
                    check(phase + '_26_original_files', stdout.count(b': OK\n') == 26)
                if command['argv'][:2] == ['xdputil', 'query']:
                    observed['dpu_query'] += 1
                    q = json.loads(stdout)
                    kernel = q['kernels'][0]
                    check(phase + '_dpu_profile', q['DPU IP Spec']['DPU Core Count'] == 1 and len(q['kernels']) == 1 and
                          kernel['DPU Arch'] == 'DPUCZDX8G_ISA1_B4096' and kernel['DPU Frequency (MHz)'] == 300 and
                          kernel['cu_addr'] == '0xa0010000' and kernel['fingerprint'] == '0x101000056010407')
                if command['argv'] == ['tpm2_getcap', '-T', 'device:/dev/tpmrm0', 'properties-fixed']:
                    observed['tpm_query'] += 1
                    check(phase + '_tpm_capability_query_succeeded', command['rc'] == 0 and bool(stdout.strip()))
            check(phase + '_all_required_observations_present_once', all(count == 1 for count in observed.values()))
            result['boot_id'] = status['boot_id']
            result['manager_pid'] = runtime['pid']
        check('warm_manager_pid_preserved', json.loads(files[phases['apply'][1] + '/runtime-state.json'])['pid'] == before['manager_pid'])
        result['classifications'] = classifications
        failures = [json.loads(data) for name, data in files.items() if name.startswith('evidence/')
                    and name.endswith('/summary.json') and not json.loads(data)['complete']]
        check('two_incomplete_apply_attempts_preserved', len(failures) == 2)
        for failure in failures:
            folder = Path(failure['evidence']).relative_to(REMOTE).as_posix()
            rollback = json.loads(files[folder + '/rollback.json'])
            check('rollback_' + folder, rollback['configuration_restored']
                  and failure['checks']['protected_vendor_client_runtime_files_unchanged'])
        result['preserved_failures'] = failures
        if mode != 'warm':
            check('fresh_boot_after_install', result['boot_id'] != OLD_BOOT)
            result['cold_boot_verified'] = False  # Physical proof is checked separately.
        if mode == 'user-coldboot':
            record_path = Path(sys.argv[4]).resolve()
            record_data = record_path.read_bytes()
            record = json.loads(record_data)
            check('user_reported_physical_restart', record['physical_power_cycle_reported_by_user']
                  and record['user_report_text'] == '已经断电启动')
            check('user_report_records_capture_limits', not record['shutdown_command_observed_for_this_cycle']
                  and not record['powerdown_serial_marker_observed_for_this_cycle']
                  and not record['startup_serial_capture_available'])
            check('restart_record_matches_both_boots', record['boot_id_before'] == OLD_BOOT
                  and record['boot_id_after'] == result['boot_id'])
            preflight = Path(record['preflight_uart_evidence'])
            uart = json.loads((preflight / 'status.json').read_text())
            check('preflight_uart_complete', uart['complete'] and uart['console_echo_restored'])
            frozen = (preflight / 'manifest.json').read_bytes()
            check('preflight_manifest_frozen', sha(frozen) == uart['manifest_sha256'])
            for command in uart['results']:
                data = (preflight / (command['id'] + '.output')).read_bytes()
                check('preflight_output_' + command['id'], command['exit_code'] == 0
                      and len(data) == command['bytes'] and sha(data) == command['output_sha256'])
            identity = json.loads((preflight / 'boot-identity.output').read_text())
            live = json.loads((preflight / 'live-nfs-configuration.output').read_text())
            check('new_boot_same_board_and_kernel', identity['boot_id'] == result['boot_id']
                  and identity['sd_cid'] == '0353445345333247805558c00401a100'
                  and identity['kernel'] == '5.15.36-xilinx-v2022.2')
            check('persistent_configuration_after_power_cycle', live['content'] == content
                  and live['sha256'] == install['configuration_sha256']
                  and sha(live['content'].encode()) == live['sha256'])
            startup = {}
            text = (preflight / 'startup-service-states.output').read_text()
            for block in text.strip().split('\n\n'):
                item = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
                startup[item['Id']] = item
            loader = startup['kv260-repaired-zocl.service']
            manager = startup['dfx-mgr.service']
            mount = startup['proc-fs-nfsd.mount']
            uptime_us = float(identity['uptime'].split()[0]) * 1000000
            check('nfs_condition_evaluated_during_startup', mount['ConditionResult'] == 'no'
                  and mount['ActiveState'] == 'inactive' and mount['Result'] == 'success'
                  and 0 < int(mount['ConditionTimestampMonotonic']) < int(manager['ExecMainStartTimestampMonotonic']) < uptime_us)
            check('nfs_servers_not_started_this_boot', all(startup[name]['UnitFileState'] == 'disabled'
                  and startup[name]['ActiveState'] == 'inactive'
                  and int(startup[name]['ExecMainStartTimestampMonotonic']) == 0 for name in install['server_services_disabled']))
            check('zocl_completed_before_manager_autostart', loader['ActiveState'] == 'active'
                  and loader['SubState'] == 'exited' and manager['UnitFileState'] == 'enabled'
                  and manager['ActiveState'] == 'active' and manager['SubState'] == 'running'
                  and 0 < int(loader['ActiveEnterTimestampMonotonic']) < int(manager['ExecMainStartTimestampMonotonic']))
            check('manager_not_restarted_by_postboot_validation', int(manager['MainPID']) == result['manager_pid'])
            status, folder, commands = phases['postboot']
            logs = {}
            for command in commands:
                if command['argv'] == ['dmesg']:
                    logs['kernel'] = files[folder + '/' + command['id'] + '.stdout'].decode('utf-8', 'replace')
                if command['argv'][:3] == ['journalctl', '-b', '-u']:
                    logs['nfs'] = files[folder + '/' + command['id'] + '.stdout'].decode('utf-8', 'replace')
                if command['argv'][:3] == ['journalctl', '-b', '--no-pager']:
                    logs['boot'] = files[folder + '/' + command['id'] + '.stdout'].decode('utf-8', 'replace')
            check('current_boot_logs_present', all(logs.get(name, '').strip() for name in ['kernel', 'nfs', 'boot']))
            check('nfs_skip_recorded_in_boot_journal', 'Condition check resulted in NFSD configuration filesystem being skipped.' in logs['nfs'])
            check('no_unsupported_nfsd_mount_failure_this_boot', not re.search(
                  r"unknown filesystem type ['\"]?nfsd|Failed to mount NFSD|Failed to start NFS (?:server|Mount)|Dependency failed for NFS", '\n'.join(logs.values()), re.I))
            check('no_kernel_fatal_signatures_this_boot', not re.search(
                  r'\bOops\b|Kernel panic|BUG:|Unable to handle kernel|Internal error:|Call trace:', logs['kernel']))
            result['user_restart_record'] = {'path': str(record_path), 'sha256': sha(record_data)}
            result['cold_boot_basis'] = 'User-confirmed physical power cycle; fresh boot ID, persisted configuration, startup states and current-boot logs independently checked.'
            result['shutdown_observed'] = False
            result['startup_serial_capture_available'] = False
            result['cold_boot_verified'] = True
        result['passed'] = True
        result['extracted'] = str(board)
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        save(out / 'review.json', result)
        save(ROOT / 'CURRENT_NFS_REVIEW.json', {'passed': result['passed'], 'review': str(out / 'review.json')})
    summary = {k: result.get(k) for k in ['passed', 'mode', 'verified_files', 'boot_id', 'manager_pid', 'error']}
    summary['review'] = str(out / 'review.json')
    print(json.dumps(summary, ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
