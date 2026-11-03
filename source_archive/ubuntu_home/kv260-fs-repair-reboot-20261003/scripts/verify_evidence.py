#!/usr/bin/env python3
"""Independently verify the transferred post-filesystem-repair evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path('/home/ghmd/kv260-fs-repair-reboot-20261003')
EVIDENCE = ROOT / 'evidence/kv260-fs-repair-reboot-20261003'
OLD_QUERY = Path('/home/ghmd/kv260-runtime-live-20261003-retry1/board_evidence/agent_logs/20-official-functional/000001-official-query.stdout')
OLD_KERNEL = Path('/home/ghmd/kv260-postboot-soak-20261003/evidence/postboot-soak/kernel-coldboot-baseline.log')
EXPECTED_TOP5 = [(258, '0.949879'), (270, '0.00931229'), (259, '0.00821807'),
                 (257, '0.00498451'), (279, '0.00388194')]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((EVIDENCE / name).read_text())


def output(name):
    return (EVIDENCE / (name + '.stdout')).read_text()


def check_manifest(root, name):
    entries = []
    invalid = []
    for line in (root / name).read_text().splitlines():
        expected, relative = line.split('  ', 1)
        path = root / relative
        if Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('Unsafe manifest member')
        entries.append(relative)
        if not path.is_file() or digest(path) != expected:
            invalid.append(relative)
    return {'entries': len(entries), 'invalid': invalid, 'passed': not invalid}


def main():
    manifest = check_manifest(EVIDENCE, 'evidence.sha256')
    commands = load('commands.json')
    runtime = load('runtime.json')
    board_summary = load('summary.json')
    query = json.loads(output('dpu-query'))
    old_query = json.loads(OLD_QUERY.read_text())
    fstab = (EVIDENCE / 'fstab.txt').read_bytes()
    old_fstab = (EVIDENCE / 'fstab-backup.txt').read_bytes()
    duplicate = b'/dev/mmcblk1p1\t/boot\tvfat\tdefaults\t0\t0\n'
    boot_entries = [line for line in fstab.decode().splitlines()
                    if line.strip() and not line.lstrip().startswith('#')
                    and len(line.split()) > 1 and line.split()[1] == '/boot']
    manager = dict(line.split('=', 1) for line in output('manager').splitlines())
    loader = dict(line.split('=', 1) for line in output('loader').splitlines())
    classified = output('classification') + (EVIDENCE / 'classification.stderr').read_text()
    top5 = [(int(index), score) for index, score in re.findall(
        r'r.index (\d+) .*?r.score ([0-9.eE+-]+)', classified)]
    journal = output('full-boot-journal')
    service = output('service-journal')
    timestamps = [float(value) for value in re.findall(r'^\[\s*([0-9.]+)\]', journal, re.M)]
    fat_warnings = [line for line in journal.splitlines() if 'FAT-fs' in line
                    and re.search(r'not properly unmounted|dirty|corrupt|error', line, re.I)]
    duplicate_warnings = [line for line in journal.splitlines()
                          if ('/boot' in line or 'boot.mount' in line)
                          and re.search(r'duplicate|already exists|File exists|failed to create', line, re.I)]
    loader_time = re.search(r'^\[\s*([0-9.]+)\].*Finished Load the previously board-tested KV260 ZOCL module', service, re.M)
    manager_time = re.search(r'^\[\s*([0-9.]+)\].*Starting dfx-mgrd Dynamic Function eXchange', service, re.M)
    stock_lines = output('stock-check').splitlines()
    stock_expected = [line.split('  ', 1)[1] for line in Path(
        '/home/ghmd/kv260-runtime-persistent-plan-20261003/stage_payload/stock.sha256').read_text().splitlines()]
    candidate_hashes = dict((path, sha) for sha, path in
                            (line.split('  ', 1) for line in output('persistent-hashes').splitlines()))
    expected_candidates = {
        '/usr/local/lib/kv260-runtime-repair/dfx-mgrd': 'db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c',
        '/usr/local/lib/kv260-runtime-repair/zocl.ko': '5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412',
    }
    archive = ROOT / 'kv260-fs-repair-reboot-20261003.tar.gz'
    stable_kernel_keys = [key for key in old_query['kernels'][0] if key != 'cu_handle']
    checks = {
        'archive_matches_board_size_and_hash': archive.stat().st_size == 59779 and digest(archive) == '440cc0a8b74abebb29268b035c2e463733e10b8bd07a47d0fe3b95ae1d1d494e',
        'board_manifest_53_files_match': manifest['passed'] and manifest['entries'] == 53,
        'uploaded_collector_matches_host_source': digest(EVIDENCE / 'collect_post_repair.py') == digest(ROOT / 'scripts/collect_post_repair.py') == '19fdf504559ae5574e89276f64537fd105132045a5090c4a1c4ed59f4bc1f8c1',
        'all_15_command_return_codes_zero': len(commands) == 15 and all(value['returncode'] == int((EVIDENCE / (name + '.rc')).read_text()) == 0 for name, value in commands.items()),
        'new_boot_matches_expected': runtime['boot_id'] == 'a7733edd-db41-4527-b8fb-cefdcbfe7b3a' and runtime['boot_id'] != runtime['previous_boot_id'],
        'same_spare_card_cid': runtime['card_cid'] == '0353445345333247805558c00401a100',
        'expected_os_and_kernel': 'VERSION_ID=2022.2_release_s10071807' in output('os-release') and runtime['kernel'] == '5.15.36-xilinx-v2022.2',
        'correct_root_and_boot_mounts': output('root-mount').split() == ['/dev/mmcblk1p2', 'ext4', '/'] and output('boot-mount').split() == ['/dev/mmcblk1p1', 'vfat', '/boot'],
        'fstab_hash_matches_reviewed_repair': hashlib.sha256(fstab).hexdigest() == runtime['fstab_sha256'] == '580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0',
        'fstab_backup_matches_original': hashlib.sha256(old_fstab).hexdigest() == runtime['fstab_backup_sha256'] == 'b1978c1e094cd260b761afbaab75f0d9e659a78044d1d4fd86807bc44ef158bd',
        'only_reviewed_duplicate_line_removed': old_fstab.count(duplicate) == 1 and old_fstab.replace(duplicate, b'', 1) == fstab and boot_entries == ['LABEL=boot        /boot   vfat    defaults    0   2'],
        'expected_repaired_zocl_loaded': runtime['zocl_srcversion'] == '9BDC942A6014BCCBD1DCB78' and runtime['enable_xgq_ert'] == '1' and runtime['zocl_refcnt'] == '0',
        'candidate_binary_hashes_match': candidate_hashes == expected_candidates,
        'manager_active_using_repaired_binary': manager['ActiveState'] == 'active' and manager['SubState'] == 'running' and manager['Result'] == 'success' and manager['ExecMainStatus'] == '0' and int(manager['MainPID']) > 0 and 'path=/usr/local/lib/kv260-runtime-repair/dfx-mgrd ;' in manager['ExecStart'] and manager['DropInPaths'] == '/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf',
        'loader_successful': loader == {'Result': 'success', 'ExecMainStatus': '0', 'ActiveState': 'active', 'SubState': 'exited'},
        'loader_finishes_before_manager_starts': bool(loader_time and manager_time and float(loader_time[1]) < float(manager_time[1])),
        'official_app_slot_zero': bool(re.search(r'^\s*kv260-benchmark-b4096\s+.*\s0,\s*$', output('apps'), re.M)),
        'original_26_stock_files_match': len(stock_expected) == len(stock_lines) == 26 and stock_lines == [path + ': OK' for path in stock_expected],
        'dpu_profile_matches_expected': query['DPU IP Spec']['DPU Core Count'] == len(query['kernels']) == 1 and all(query['kernels'][0][key] == value for key, value in {'DPU Arch': 'DPUCZDX8G_ISA1_B4096', 'DPU Frequency (MHz)': 300, 'cu_addr': '0xa0010000', 'fingerprint': '0x101000056010407'}.items()),
        'dpu_ip_and_stable_kernel_fields_match_prior_baseline': query['DPU IP Spec'] == old_query['DPU IP Spec'] and all(query['kernels'][0][key] == old_query['kernels'][0][key] for key in stable_kernel_keys),
        'runtime_libraries_match_prior_baseline': query['VAI Version'] == old_query['VAI Version'],
        'exact_original_classification_inputs': commands['classification']['argv'] == ['/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification', '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel', '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'],
        'full_top5_matches_baseline': top5 == EXPECTED_TOP5,
        'full_boot_journal_covers_boot_and_inference': bool(timestamps and min(timestamps) == 0 and max(timestamps) > runtime['boot_uptime_seconds'] and 'ERT_EXEC_WRITE' in journal),
        'no_fat_dirty_warning_in_collected_boot': not fat_warnings,
        'no_duplicate_boot_warning_in_collected_boot': not duplicate_warnings,
        'board_summary_all_15_checks_passed': len(board_summary['checks']) == 15 and all(board_summary['checks'].values()) and board_summary['all_passed'],
    }
    old_kernel = OLD_KERNEL.read_text()
    patterns = {
        'nfsd_mount_failure': r'Failed to mount NFSD|proc-fs-nfsd.mount: Failed|Dependency failed for NFS',
        'overlay_memory_leak_warning': r'OF: overlay: WARNING',
        'irq_index_8_not_found': r'IRQ index 8 not found',
        'ert_exec_write_deprecated': r'ERT_EXEC_WRITE is obsoleted',
        'aie_resources_skip_minus22': r'AIE_RESOURCES.*return code: -22',
        'other_optional_xclbin_section_skips': r'(DEBUG_IP_LAYOUT|AIE_METADATA).*return code: -22',
        'clock_permission_errors': r'(set divider failed|clock disable failed)',
        'tpm_self_test_error': r'TPM error.*self test',
        'fuse_module_missing': r"Failed to find module 'fuse'",
        'audio_configuration_errors': r'alsactl.*(failed|error:)',
        'desktop_icon_errors': r'Error loading icon:',
    }
    groups = {}
    for name, pattern in patterns.items():
        lines = [line for line in journal.splitlines() if re.search(pattern, line)]
        groups[name] = {'current_lines': lines, 'prior_kernel_baseline_contains_same_pattern': bool(re.search(pattern, old_kernel))}
    failure_candidates = [line for line in journal.splitlines() if re.search(
        r'error|fail|warning|dirty|corrupt|obsolet|IRQ index|\bBUG\b|panic|Call Trace|segfault|timed out|skip kind', line, re.I)]
    kernel_review = {
        'journal_monotonic_range_seconds': [min(timestamps), max(timestamps)],
        'fat_warning_lines': fat_warnings,
        'duplicate_boot_warning_lines': duplicate_warnings,
        'failed_units_raw': output('failed-units'),
        'warning_groups': groups,
        'keyword_candidates': failure_candidates,
        'prior_kernel_evidence': str(OLD_KERNEL),
        'qualification': 'Prior kernel comparison does not cover all userspace messages. Keyword review is not proof of absence of every possible issue. Existing warnings are retained and not repaired by this check.',
    }
    (ROOT / 'KERNEL_REVIEW.json').write_text(json.dumps(kernel_review, ensure_ascii=False, indent=2) + '\n')
    result = {
        'host_verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'checks': checks, 'all_checks_passed': all(checks.values()),
        'board_manifest': manifest, 'runtime': runtime, 'top5': top5,
        'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
        'loader_finished_boot_seconds': float(loader_time[1]) if loader_time else None,
        'manager_start_boot_seconds': float(manager_time[1]) if manager_time else None,
        'journal_monotonic_range_seconds': kernel_review['journal_monotonic_range_seconds'],
        'scope': 'Post-filesystem-repair cold boot, persistent runtime, original single model/image functional acceptance; no new load test or hardware deployment.',
    }
    (ROOT / 'HOST_VERIFICATION.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'checks': len(checks), 'all_passed': result['all_checks_passed'],
                      'failed_checks': [key for key, value in checks.items() if not value],
                      'board_manifest_files': manifest['entries'],
                      'journal_range': result['journal_monotonic_range_seconds']}))
    return 0 if result['all_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
