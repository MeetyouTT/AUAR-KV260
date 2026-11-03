#!/usr/bin/env python3
"""Gate the capacity experiment on actual joint reports, keeping release separate."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
status = json.loads((ROOT / 'CURRENT_FPGA.json').read_text())
assert status['state'] == 'finished' and status['rc'] == 0, status
assert status.get('source_files_changed_during_run') == [], 'Source changed during implementation'
out = Path(status['evidence'])
assert hashlib.sha256((out / 'fit_checkpoint.tcl').read_bytes()).hexdigest() == status['script_sha256'], 'Implementation script snapshot changed'
for name, expected in status['available_source_sha256'].items():
    assert hashlib.sha256((out / 'source_archive' / name).read_bytes()).hexdigest() == expected, 'Archived source changed: ' + name
console = (out / 'console.log').read_text()
def limited_messages(log):
    return re.findall(r"Message '([^']+)' appears \d+ times and further instances of the messages will be disabled", log)
assert re.search(r'^AURA_ADAPT_JOINT_ROUTED$', console, re.M)
assert not re.search(r'^AURA_ADAPT_ERROR=', console, re.M)
# Resuming a placed checkpoint retains its physical reuse data. Keep the
# original implementation warnings and checkpoint chain visible as well.
ancestry = []
reference_statuses = [status]
prior = status
seen = set()
while prior.get('resume_checkpoint'):
    checkpoint = Path(prior['resume_checkpoint']).resolve()
    assert ROOT in checkpoint.parents and checkpoint not in seen
    seen.add(checkpoint)
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == prior['resume_sha256']
    parent_out = checkpoint.parent
    parent_status = json.loads((parent_out / 'status.json').read_text())
    reference_statuses.append(parent_status)
    parent_console = (parent_out / 'console.log').read_text()
    ancestry.append({'checkpoint': str(checkpoint), 'sha256': prior['resume_sha256'],
                     'parent_state': parent_status['state'],
                     'incremental_directive': parent_status.get('incremental_directive', 'inherited/default'),
                     'message_ids_with_display_limits': limited_messages(parent_console),
                     'critical_warnings': re.findall(r'^CRITICAL WARNING:.*$', parent_console, re.M)})
    prior = parent_status
references = {}
for prior_status in reference_statuses:
    if not prior_status.get('incremental_reference'):
        continue
    reference = Path(prior_status['incremental_reference']).resolve()
    expected = prior_status['incremental_reference_sha256']
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == expected, 'Incremental reference changed'
    row = {'checkpoint': str(reference), 'sha256': expected,
           'directive': prior_status.get('incremental_directive', 'RuntimeOptimized')}
    if ROOT in reference.parents:
        reference_status = json.loads((reference.parent / 'status.json').read_text())
        assert reference_status['state'] == 'finished' and reference_status['rc'] == 0
        archived = reference.parent / 'verification.json'
        if archived.is_file():
            row['source_verification'] = str(archived)
            row['source_verification_sha256'] = hashlib.sha256(archived.read_bytes()).hexdigest()
    else:
        assert expected == '4a564eb33412124544dd942c74ff682ccd529d29e739e41dbce28aa94232face', 'Unexpected external reference'
    references[str(reference)] = row
names = ['joint_utilization.rpt', 'motion_joint_utilization.rpt', 'joint_timing.rpt',
         'joint_route.rpt', 'joint_drc.rpt', 'joint_check_timing.rpt',
         'joint_clocks.rpt', 'pwm_pad_timing.rpt', 'io_binding.txt', 'joint_routed.dcp']
hashes = {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in names}
signoff_names = ['joint_bus_skew.rpt', 'joint_io.rpt', 'joint_binding_properties.tsv']
signoff_present = all((out / name).is_file() for name in signoff_names)
bus_skew_slacks = []
signoff_verified = False
audit = None
if signoff_present:
    hashes.update({name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in signoff_names})
    signoff_console = console
    if (out / 'signoff_audit.json').is_file():
        audit = json.loads((out / 'signoff_audit.json').read_text())
        assert audit['state'] == 'finished' and audit['rc'] == 0
        assert audit['checkpoint_sha256'] == hashes['joint_routed.dcp']
        audit_out = Path(audit['evidence']).resolve()
        assert ROOT in audit_out.parents
        for name, expected in audit['script_sha256'].items():
            assert hashlib.sha256((audit_out / name).read_bytes()).hexdigest() == expected
        for name in signoff_names:
            assert hashlib.sha256((audit_out / name).read_bytes()).hexdigest() == hashes[name]
        signoff_console = (audit_out / 'console.log').read_text()
    bus = (out / 'joint_bus_skew.rpt').read_text()
    bus_skew_slacks = [float(value) for value in re.findall(r'Slack\s*\((?:MET|VIOLATED)\)\s*:\s*([-+\d.]+)ns', bus)]
    signoff_verified = (bool(bus_skew_slacks) and min(bus_skew_slacks) >= 0
                        and 'VIOLATED' not in bus
                        and bool(re.search(r'^AURA_SIGNOFF_PROPERTIES_VERIFIED$', signoff_console, re.M)))
timing = (out / 'joint_timing.rpt').read_text()
assert re.search(r'\| Device\s*:\s*xck26-sfvc784', timing)
assert re.search(r'\| Speed File\s*:\s*-2LV\b', timing)
summary = re.search(r'WNS\(ns\).*?\n\s*[- ]+\n\s*([^\n]+)', timing, re.S)
assert summary, 'Timing summary not found'
values = summary.group(1).split()
assert len(values) == 12, values
keys = ['wns_ns', 'tns_ns', 'setup_failing', 'setup_total', 'whs_ns', 'ths_ns',
        'hold_failing', 'hold_total', 'wpws_ns', 'tpws_ns', 'pulse_failing', 'pulse_total']
metrics = {k: float(v) if k.endswith('_ns') else int(v) for k, v in zip(keys, values)}
assert metrics['setup_total'] > 0 and metrics['hold_total'] > 0, 'Empty timing analysis'
util = (out / 'joint_utilization.rpt').read_text()
resources = {}
for name in ['CLB LUTs', 'CLB Registers', 'CLB', 'Block RAM Tile', 'URAM', 'DSPs']:
    match = re.search(r'^\|\s*' + re.escape(name) + r'\*?\s*\|([^\n]+)', util, re.M)
    assert match, name
    columns = [c.strip() for c in match.group(1).split('|') if c.strip()]
    resources[name] = {'used': float(columns[0]), 'available': float(columns[-2]),
                       'utilization_percent': float(columns[-1])}
motion_util = (out / 'motion_joint_utilization.rpt').read_text()
motion_resources = {}
for name in ['CLB LUTs', 'CLB Registers']:
    match = re.search(r'^\|\s*' + re.escape(name) + r'\*?\s*\|\s*(\d+)', motion_util, re.M)
    assert match, 'Missing motion resource: ' + name
    motion_resources[name] = int(match.group(1))
assert all(value > 0 for value in motion_resources.values()), 'Motion logic absent'
route = (out / 'joint_route.rpt').read_text()
def nets(label):
    match = re.search(re.escape(label) + r'\.*\s*:\s*(\d+)', route)
    assert match, label
    return int(match.group(1))
route_metrics = {label: nets(label) for label in ['# of routable nets', '# of fully routed nets', '# of nets with routing errors']}
drc = (out / 'joint_drc.rpt').read_text()
drc_rules = re.findall(r'^\|\s*([\w-]+)\s*\|\s*(Warning|Error|Critical Warning)\s*\|([^|]+)\|\s*(\d+)\s*\|', drc, re.M)
violations = re.search(r'Violations found:\s*(\d+)', drc)
assert violations, 'DRC summary absent'
assert sum(int(row[3]) for row in drc_rules) == int(violations.group(1)), 'Unparsed DRC rules'
checks = (out / 'joint_check_timing.rpt').read_text()
gaps = {k: int(v) for k, v in re.findall(r'checking (\w+) \((\d+)\)', checks)}
binding = (out / 'io_binding.txt').read_text()
assert 'PHYSICAL=J2.3/E10' in binding and 'NEW_ROLE=servo_pwm' in binding
clocks = (out / 'joint_clocks.rpt').read_text()
clock_periods = {}
for frequency, expected in [(50, 20.000), (100, 10.000), (200, 5.000), (300, 3.333), (600, 1.667)]:
    name = f'clk_{frequency}M_kv260_ispMipiRx_vcu_DP_clk_wiz_0_0'
    match = re.search(r'^' + re.escape(name) + r'\s+([\d.]+)\s+\{', clocks, re.M)
    assert match, 'Missing reference clock: ' + name
    period = float(match.group(1))
    assert period == expected, 'Clock period changed: ' + name
    clock_periods[name] = period
pad = (out / 'pwm_pad_timing.rpt').read_text()
assert 'lrclk_tx' in pad and re.search(r'Path Type:\s+Max', pad), 'PWM pad path absent'
pad_slack = re.search(r'Slack\s*\((?:MET|VIOLATED)\)\s*:\s*([-+\d.]+)ns', pad)
assert pad_slack, 'PWM pad slack absent'
passed = (all(metrics[k] >= 0 for k in ['wns_ns', 'whs_ns', 'wpws_ns'])
          and all(metrics[k] == 0 for k in ['setup_failing', 'hold_failing', 'pulse_failing'])
          and route_metrics['# of nets with routing errors'] == 0
          and route_metrics['# of routable nets'] == route_metrics['# of fully routed nets']
          and not any(severity in ['Error', 'Critical Warning'] for _, severity, _, _ in drc_rules)
          and all(gaps.get(k, -1) == 0 for k in ['no_clock', 'constant_clock', 'pulse_width_clock',
                                              'unconstrained_internal_endpoints', 'multiple_clock',
                                              'loops', 'latch_loops'])
          and float(pad_slack.group(1)) >= 0
          and all(0 <= row['used'] <= row['available'] for row in resources.values())
          and resources['DSPs']['used'] == 710 and resources['URAM']['used'] == 56)
passed = passed and signoff_verified
result = {'capacity_candidate_passed': passed, 'formal_release_passed': False,
          'board_verified': False, 'single_axis': True, 'evidence': str(out),
          'timing': metrics, 'resources': resources, 'motion_resources': motion_resources,
          'route': route_metrics,
          'implementation_critical_warnings': re.findall(r'^CRITICAL WARNING:.*$', console, re.M),
          'message_ids_with_display_limits': limited_messages(console),
          'checkpoint_ancestry': ancestry,
          'incremental_references': list(references.values()),
          'drc_rule_counts': {rule: {'severity': severity, 'count': int(count)} for rule, severity, _, count in drc_rules},
          'timing_check_counts': gaps, 'io_binding': binding,
          'clock_periods_ns': clock_periods,
          'physical_signoff_present': signoff_present,
          'physical_signoff_verified': signoff_verified,
          'bus_skew_worst_slack_ns': min(bus_skew_slacks) if bus_skew_slacks else None,
          'signoff_audit': audit,
          'pwm_pad_slack_ns': float(pad_slack.group(1)),
          'report_sha256': hashes,
          'limits': ['CPU identity is a separate board test', 'Formal dual-axis ABI and calibration are not in this candidate',
                     'External legacy I/O timing gaps remain explicitly reported', 'No PL reload or mechanical activation']}
(ROOT / 'fpga/verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['capacity_candidate_passed', 'evidence', 'timing', 'resources',
                                      'motion_resources', 'route', 'physical_signoff_verified',
                                      'bus_skew_worst_slack_ns', 'pwm_pad_slack_ns']}, indent=2))
raise SystemExit(0 if passed else 1)
