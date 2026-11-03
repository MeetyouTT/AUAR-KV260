#!/usr/bin/env python3
"""Independently verify the preserved board data against the known baseline."""
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
baseline = Path('/home/ghmd/kv260-runtime-live-20261003-retry1/board_evidence/agent_logs/20-official-functional/000001-official-query.stdout')
checks = {}
manifest = (root / 'evidence.sha256').read_text().splitlines()
invalid = []
for line in manifest:
    digest, name = line.split('  ', 1)
    path = root / name
    if path.parent != root or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        invalid.append(name)
checks['board_evidence_hashes'] = not invalid

expected = [(258, '0.949879'), (270, '0.00931229'), (259, '0.00821807'),
            (257, '0.00498451'), (279, '0.00388194')]
logs = sorted(root.glob('run-*.log'))
checks['exactly_60_classification_logs'] = len(logs) == 60
checks['all_60_top5_match'] = len(logs) == 60 and all(
    [(int(a), b) for a, b in re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)', p.read_text())] == expected
    for p in logs)
rows = (root / 'summary.csv').read_text().splitlines()[1:]
checks['all_60_return_codes_zero'] = len(rows) == 60 and all(row.split(',', 3)[2] == '0' for row in rows)
states = (root / 'state.csv').read_text().splitlines()
checks['manager_and_refcounts_stable'] = len(states) == 60 and all(
    ',manager_pid=1012,zocl_refcnt=0,' in row for row in states)

runtime = json.loads((root / 'runtime-final.json').read_text())
checks['same_boot_id'] = runtime['boot_id'] == '0251d729-0d3c-44e8-abb9-27121306c081'
checks['same_spare_card_cid'] = runtime['card_cid'] == '0353445345333247805558c00401a100'
checks['fixed_zocl_still_loaded'] = runtime['zocl_srcversion'] == '9BDC942A6014BCCBD1DCB78' and runtime['zocl_refcnt'] == '0'
checks['final_query_rc_zero'] = (root / 'dpu-query-final.rc').read_text().strip() == '0'
query = json.loads((root / 'dpu-query-final.stdout').read_text())
golden = json.loads(baseline.read_text())
kernels = query['kernels']
checks['final_dpu_profile_matches'] = query['DPU IP Spec']['DPU Core Count'] == 1 and len(kernels) == 1 and all(
    kernels[0][key] == value for key, value in {
        'DPU Arch': 'DPUCZDX8G_ISA1_B4096', 'DPU Frequency (MHz)': 300,
        'cu_addr': '0xa0010000', 'fingerprint': '0x101000056010407'
    }.items())
checks['runtime_libraries_match_original_query'] = query['VAI Version'] == golden['VAI Version']
stock = (root / 'stock-check-final.stdout').read_text()
checks['stock_26_hashes_match'] = (root / 'stock-check-final.rc').read_text().strip() == '0' and stock.count(': OK\n') == 26
manager = (root / 'manager-state-final.stdout').read_text()
loader = (root / 'loader-state-final.stdout').read_text()
checks['manager_active_and_repaired'] = all(v in manager for v in ['MainPID=1012', 'ActiveState=active', 'Result=success', '/usr/local/lib/kv260-runtime-repair/dfx-mgrd'])
checks['loader_successful'] = all(v in loader for v in ['ActiveState=active', 'Result=success', 'ExecMainStatus=0'])
apps = (root / 'apps-final.stdout').read_text()
checks['official_app_slot_zero'] = bool(re.search(r'^\s*kv260-benchmark-b4096\s+.*\s0,\s*$', apps, re.M))

duration = json.loads((root / 'duration.json').read_text())
start = duration['launcher_start_boot_seconds']
end = duration['observer_detected_finish_boot_seconds']
kernel = (root / 'kernel-final.stdout').read_text().splitlines()
within = []
for line in kernel:
    match = re.match(r'^\[\s*([0-9.]+)\]', line)
    if match and start <= float(match.group(1)) <= end:
        within.append(line)
pattern = re.compile(r'error|fail|warn|oops|BUG:|Call Trace|panic|timeout|timed out|segfault', re.I)
suspicious = [line for line in within if pattern.search(line)]
kernel_review = {'scope_boot_seconds': [start, end], 'retained_loop_lines': len(within),
                 'keyword_candidates': suspicious,
                 'limitation': 'keyword screening supplements manual review; it does not detect every possible kernel issue'}
(root.parent.parent / 'KERNEL_REVIEW.json').write_text(json.dumps(kernel_review, indent=2) + '\n')
journal_root = root.parent / 'postboot-soak-kernel'
journal_bad = []
for line in (journal_root / 'evidence.sha256').read_text().splitlines():
    digest, name = line.split('  ', 1)
    path = journal_root / name
    if path.parent != journal_root or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        journal_bad.append(name)
checks['supplementary_kernel_hashes_match'] = not journal_bad
capture = json.loads((journal_root / 'capture.json').read_text())
checks['kernel_journal_from_same_boot'] = capture['return_code'] == 0 and capture['boot_id'] == runtime['boot_id']
timed = []
for line in (journal_root / 'kernel-journal-full.log').read_text().splitlines():
    match = re.match(r'^\[\s*([0-9.]+)\]', line)
    if match:
        timed.append((float(match.group(1)), line))
interval = [(t, line) for t, line in timed if start <= t <= end]
checks['kernel_journal_covers_loop'] = bool(interval) and timed[0][0] <= start and timed[-1][0] >= end and interval[0][0] - start < 5 and end - interval[-1][0] < 5
journal_candidates = [line for t, line in interval if pattern.search(line)]
aie_skip = [line for t, line in interval if 'skip kind 29(AIE_RESOURCES) return code: -22' in line]
checks['no_failure_keyword_candidates_in_loop_journal'] = not journal_candidates
journal_review = {
    'loop_boot_seconds': [start, end], 'journal_range_boot_seconds': [timed[0][0], timed[-1][0]],
    'loop_first_record_boot_seconds': interval[0][0], 'loop_last_record_boot_seconds': interval[-1][0],
    'loop_line_count': len(interval), 'failure_keyword_candidates': journal_candidates,
    'aie_resources_skip_minus22_count': len(aie_skip),
    'aie_resources_skip_also_in_coldboot_baseline': 'skip kind 29(AIE_RESOURCES) return code: -22' in (root / 'kernel-coldboot-baseline.log').read_text(),
    'qualification': 'The -22 AIE section skip messages remain present; they did not prevent successful classification. Kernel keyword screening is not proof of absence of every possible defect.',
}
(root.parent.parent / 'KERNEL_JOURNAL_REVIEW.json').write_text(json.dumps(journal_review, indent=2) + '\n')
output = {
    'checks': checks, 'all_checks_passed': all(checks.values()),
    'board_manifest_entries': len(manifest), 'invalid_manifest_files': invalid,
    'duration': duration, 'kernel_review': kernel_review, 'full_kernel_journal_review': journal_review,
    'summary': json.loads((root / 'summary.json').read_text()),
    'scope': 'sampled post-reboot functional observation; whole-card image not yet created',
}
(root.parent.parent / 'HOST_VERIFICATION.json').write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(output, indent=2, ensure_ascii=False))
raise SystemExit(0 if all(checks.values()) else 1)
