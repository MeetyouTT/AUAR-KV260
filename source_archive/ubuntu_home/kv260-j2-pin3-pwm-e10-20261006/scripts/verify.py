#!/usr/bin/env python3
"""Check offline evidence and artifacts. No board or MMIO access."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
from connector_mapping import audit

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bit_payload(data):
    pos = 0
    length = struct.unpack_from('>H', data, pos)[0]
    pos += 2 + length
    key_length = struct.unpack_from('>H', data, pos)[0]
    assert key_length == 1
    pos += 2
    fields = {}
    while pos < len(data):
        tag = chr(data[pos])
        pos += 1
        if tag == 'e':
            length = struct.unpack_from('>I', data, pos)[0]
            pos += 4
            assert pos + length == len(data)
            return fields, data[pos:]
        assert tag in 'abcd'
        length = struct.unpack_from('>H', data, pos)[0]
        pos += 2
        fields[tag] = data[pos:pos + length].rstrip(b'\x00').decode()
        pos += length
    raise ValueError('No BIT payload')


sim = json.loads((ROOT / 'CURRENT_SIM.json').read_text())
build = json.loads((ROOT / 'CURRENT_BUILD.json').read_text())
out = Path(build['evidence'])
checks = []


def check(label, passed, detail=None):
    checks.append({'check': label, 'passed': bool(passed), 'detail': detail})


check('simulation_and_build_completed', sim['complete'] and build['complete'])
check('same_rtl_simulated_and_built', sim['rtl_sha256'] == build['rtl_sha256'])
for relative, expected in build['rtl_sha256'].items():
    check('current_rtl:' + relative, digest(ROOT / relative) == expected)
    packaged = out / 'ip_repo/aura_pwm_probe/src' / Path(relative).name
    check('packaged_rtl:' + relative, digest(packaged) == expected)
for relative, expected in build['input_sha256'].items():
    check('build_input:' + relative, digest(ROOT / relative) == expected)

identity = json.loads((out / 'source_identity.json').read_text())
for path, expected in identity['inputs'].items():
    check('identity_input:' + path, digest(Path(path)) == expected)
check('identity_snapshot_unchanged', identity == json.loads(
    (ROOT / 'evidence/source_identity.json').read_text()))

for stage in (sim, build):
    for command in stage['commands']:
        log = Path(stage['evidence']) / (command['label'] + '.log')
        content = log.read_text(errors='replace')
        actual_hash = hashlib.sha256(content.encode()).hexdigest()
        check(stage['phase'] + '_log:' + command['label'],
              command['rc'] == 0 and command['passed'] and
              actual_hash == command['log_sha256'] and
              (not command['marker'] or command['marker'] in content) and
              not re.search(r'^(Fatal:|ERROR:|CRITICAL WARNING:)', content, re.M))

burst_log = (Path(sim['evidence']) / 'tb_burst-run.log').read_text()
check('burst_cases', len(re.findall(r'^BURST_CASE_PASS ', burst_log, re.M)) == 15)
check('static_high_continuous', 'CLK_HZ=10000 HZ=10 US=100000 FRAMES=0 VALID=1' in burst_log)
check('static_high_real_clock', 'CLK_HZ=99999001 HZ=10 US=100000 FRAMES=1 VALID=1' in burst_log)
check('full_duty_bounded', 'CLK_HZ=10000 HZ=50 US=20000 FRAMES=3 VALID=1' in burst_log)
check('square10_continuous', 'CLK_HZ=10000 HZ=10 US=50000 FRAMES=0 VALID=1' in burst_log)
check('square10_real_clock', 'CLK_HZ=99999001 HZ=10 US=50000 FRAMES=1 VALID=1' in burst_log)
check('250_frame_expiration', 'CLK_HZ=10000 HZ=50 US=1500 FRAMES=250 VALID=1' in burst_log)
check('continuous_mode_and_STOP', 'CLK_HZ=10000 HZ=50 US=1500 FRAMES=0 VALID=1' in burst_log)
check('real_clock_tick_case', 'CLK_HZ=99999001 HZ=50 US=1500 FRAMES=3 VALID=1' in burst_log)
axi_log = (Path(sim['evidence']) / 'tb_axi-run.log').read_text()
check('axi_coverage_marker', 'AURA_AXI_ALL_PASS strobes=16' in axi_log)
check('axi_static_high', '/static_high/stop' in axi_log)

bd = json.loads((out / 'project/pwm_bench.srcs/sources_1/bd/pwm_bench/pwm_bench.bd')
                .read_text())['design']
params = bd['components']['probe']['parameters']
check('fixed_bench_parameters', all(params[k]['value'] == str(v) for k, v in {
    'CLK_HZ': 99999001, 'PWM_HZ': 50, 'PULSE_US': 1500, 'RUN_FRAMES': 0}.items()))
segments = bd['addressing']['/PS_0']['address_spaces']['Data']['segments']
segment = segments['SEG_probe_reg0']
check('axi_address', int(segment['offset'], 16) == 0x80080000 and segment['range'] == '4K')
nets = bd['nets']
check('aux_reset_deasserted', 'reset_ctrl/aux_reset_in' in nets['one_dout']['ports'])
check('debug_reset_deasserted', 'reset_ctrl/mb_debug_sys_rst' in nets['zero_dout']['ports'])
check('ps_reset_connected', set(nets['PS_0_pl_resetn0']['ports']) == {
    'PS_0/pl_resetn0', 'reset_ctrl/ext_reset_in'})
reset_source = (out / 'project/pwm_bench.gen/sources_1/bd/pwm_bench/ip/'
                'pwm_bench_reset_ctrl_0/synth/pwm_bench_reset_ctrl_0.vhd').read_text()
check('propagated_reset_polarities', 'C_EXT_RESET_HIGH=0,C_AUX_RESET_HIGH=0' in reset_source)
platform = (out / 'platform.txt').read_text()
check('platform_part_clock', 'PART=xck26-sfvc784-2LV-c' in platform and
      'CLOCK_HZ=99999001' in platform)

result = json.loads((out / 'build_result.json').read_text())
check('setup_hold_drc', result['wns_ns'] >= 0 and result['whs_ns'] >= 0 and
      result['drc_errors'] == 0, result)
check('async_output_budget', result['output_budget_ns'] == 20.0 and
      0 <= result['output_slack_ns'] <= 20.0)
io = (out / 'io.rpt').read_text()
check('output_pin', bool(re.search(
    r'^\| E10\s+\| servo_pwm\s+\|[^\n]*OUTPUT\s+\| LVCMOS33\s+\|\s+45\s+\|\s+4\s+\|[^\n]*SLOW', io, re.M)))
pin_review = audit()
check('connector_mapping_matches_intended_pin', pin_review['passed'], pin_review)
timing = (out / 'timing.rpt').read_text()
check('internal_timing_coverage', all('checking ' + name + ' (0)' in timing for name in
      ['no_clock', 'constant_clock', 'unconstrained_internal_endpoints']))

artifacts = out / 'artifacts'
fields, payload = bit_payload((artifacts / 'aura_pwm_probe.bit').read_bytes())
check('bit_header_part', fields['b'] == 'xck26-sfvc784-2LV-c', fields)
check('bin_matches_bit_payload', payload == (artifacts / 'aura_pwm_probe.bin').read_bytes())
with zipfile.ZipFile(artifacts / 'aura_pwm_probe.xsa') as xsa:
    bit_names = [name for name in xsa.namelist() if name.endswith('.bit')]
    check('xsa_embedded_bit', len(bit_names) == 1 and
          xsa.read(bit_names[0]) == (artifacts / 'aura_pwm_probe.bit').read_bytes(), bit_names)

manifest = {str(p.relative_to(ROOT)): {'size': p.stat().st_size, 'sha256': digest(p)}
            for p in sorted(artifacts.iterdir()) if p.is_file()}
report = {'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'passed': all(c['passed'] for c in checks), 'checks': checks,
          'simulation_evidence': sim['evidence'], 'build_evidence': str(out),
          'build_id': identity['build_id'], 'artifacts': manifest,
          'board_accessed': False, 'waveform_measured': False, 'servo_actuated': False,
          'voltage': {'source': 'not_measured_for_this_candidate', 'reported_normal': False,
                      'exact_readings_received': False},
          'includes_dpu': False}
(ROOT / 'FINAL_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'passed': report['passed'], 'checks': len(checks),
                  'failed': [c['check'] for c in checks if not c['passed']],
                  'build_id': report['build_id']}))
raise SystemExit(0 if report['passed'] else 1)
