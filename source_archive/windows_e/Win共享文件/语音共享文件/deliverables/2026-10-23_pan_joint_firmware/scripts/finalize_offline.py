#!/usr/bin/env python3
"""Audit and package a host-only motor/DPU candidate; never deploy or qualify it."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from bitstream_pairing import check_pairing

ROOT = Path(__file__).resolve().parent
PARENT = Path('/home/ghmd/kv260-visual-servo-20261007')
TOOLS = Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin')
FDT = Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin')
DTC = Path('/home/ghmd/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2')
M3 = Path('/home/ghmd/kv260-m3-axilite-20261002/test_bundle_attempt02')
APP = 'aura-visual-servo-b4096-v2'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_reports(directory):
    timing = (directory / 'timing.rpt').read_text()
    summary = re.search(r'WNS\(ns\).*?\n\s*[- ]+\n\s*([^\n]+)', timing, re.S)
    require(summary is not None, 'Timing summary missing')
    values = summary.group(1).split()
    keys = ['wns_ns', 'tns_ns', 'setup_failing', 'setup_total', 'whs_ns', 'ths_ns',
            'hold_failing', 'hold_total', 'wpws_ns', 'tpws_ns', 'pulse_failing', 'pulse_total']
    require(len(values) == len(keys), 'Timing summary shape mismatch')
    metrics = {k: float(v) if k.endswith('_ns') else int(v) for k, v in zip(keys, values)}
    require(all(metrics[k] >= 0 for k in ['wns_ns', 'whs_ns', 'wpws_ns']), 'Negative timing slack')
    require(all(metrics[k] == 0 for k in ['setup_failing', 'hold_failing', 'pulse_failing']), 'Failing timing endpoints')
    require(metrics['setup_total'] > 0 and metrics['hold_total'] > 0, 'Empty timing analysis')
    route = (directory / 'route.rpt').read_text()
    nets = {}
    for key in ['# of routable nets', '# of fully routed nets', '# of nets with routing errors']:
        match = re.search(re.escape(key) + r'\.*\s*:\s*(\d+)', route)
        require(match is not None, 'Route summary missing: ' + key)
        nets[key] = int(match[1])
    require(nets['# of routable nets'] == nets['# of fully routed nets'] > 0
            and nets['# of nets with routing errors'] == 0, 'Incomplete routing')
    drc = (directory / 'drc.rpt').read_text()
    rows = re.findall(r'^\|\s*([\w-]+)\s*\|\s*(Warning|Error|Critical Warning)\s*\|([^|]+)\|\s*(\d+)\s*\|', drc, re.M)
    total = re.search(r'Violations found:\s*(\d+)', drc)
    require(total is not None and sum(int(r[3]) for r in rows) == int(total[1]), 'DRC counts incomplete')
    require(not any(r[1] != 'Warning' for r in rows), 'DRC error or critical warning')
    bus = (directory / 'bus_skew.rpt').read_text()
    slacks = [float(x) for x in re.findall(r'Slack\s*\((?:MET|VIOLATED)\)\s*:\s*([-+\d.]+)ns', bus)]
    require(bool(slacks) and min(slacks) >= 0 and 'VIOLATED' not in bus, 'Bus skew failure')
    grouped_checks = {}
    for key, value in re.findall(r'checking (\w+) \((\d+)\)', (directory / 'check_timing.rpt').read_text()):
        grouped_checks.setdefault(key, []).append(int(value))
    require(all(len(set(values)) == 1 for values in grouped_checks.values()), 'Inconsistent repeated timing counts')
    checks = {key: values[0] for key, values in grouped_checks.items()}
    require(all(checks.get(k, -1) == 0 for k in ['no_clock', 'constant_clock', 'pulse_width_clock',
            'unconstrained_internal_endpoints', 'multiple_clock', 'generated_clocks', 'loops',
            'partial_input_delay', 'partial_output_delay', 'latch_loops']), 'Internal timing coverage gap')
    pad = (directory / 'pwm_timing.rpt').read_text()
    require('servo_pwm_reg/C' in pad and 'period=10.000ns' in pad
            and 'Destination:            servo_pwm' in pad, 'PWM timing path mismatch')
    return {'timing': metrics, 'route': nets, 'bus_skew_worst_slack_ns': min(slacks),
            'drc_warnings': {r[0]: int(r[3]) for r in rows},
            'external_timing_gaps': {k: checks[k] for k in ['no_input_delay', 'no_output_delay']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-audit', action='store_true')
    args = parser.parse_args()
    os.nice(15)
    out = ROOT / 'final-audit'
    out.mkdir(exist_ok=True)
    script = (PARENT / 'scripts/audit_joint.tcl').read_text().replace('general.maxThreads 4', 'general.maxThreads 1')
    preamble = ('set ::env(AURA_AUDIT_SOURCE_PLATFORM) 1\n'
                'set ::env(AURA_AUDIT_OUT) [file normalize /home/ghmd/aura-pan-joint-20261023/final-audit]\n'
                'set ::env(AURA_AUDIT_DCP) [file normalize /home/ghmd/aura-pan-joint-20261023/implementation/source_routed.dcp]\n')
    (ROOT / 'audit-final.tcl').write_text(preamble + script)
    if args.prepare_audit:
        print('Prepared audit-final.tcl; no Vivado or hardware access')
        return
    status = json.loads((ROOT / 'STATUS.json').read_text())
    implementation_log = ROOT / status.get('implementation_log', 'implement-host.log')
    require(re.search(r'^AURA_SOURCE_PLATFORM_IMPLEMENTED$', implementation_log.read_text(), re.M) is not None,
            'Implementation success marker missing')
    for name, digest in status['source_sha256'].items():
        require(sha(name) == digest, 'Source changed: ' + name)
    frozen_root = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_safe_completion')
    for row in json.loads((frozen_root / 'verification.json').read_text())['files']:
        relative = Path(row['path'])
        if relative.parts[0] in {'rtl', 'native', 'runtime', 'tests', 'config', 'scripts'}:
            require(sha(ROOT / 'candidate' / relative) == row['sha256'], 'Frozen candidate drift: ' + row['path'])
    validation = json.loads((ROOT / 'validation-summary.json').read_text())
    require(validation['software_total'] == 51 and len(validation['rtl']) == 3
            and validation['pwm_scenarios'] == 9, 'Software/RTL acceptance incomplete')
    for row in validation['rtl']:
        require(row['passed'] is True and sha(ROOT / row['log']) == row['sha256'], 'RTL result changed')
    gtk = json.loads((ROOT / 'gtk-input-check.json').read_text())
    require(gtk['status'] == 'REAL_GTK_XSERVER_INPUT_FAKE_HARDWARE_PASS'
            and len(gtk['checks']) == 6 and gtk['board_accessed'] is False, 'GTK input checks incomplete')
    require(sha(ROOT / 'implement-resume.tcl') == status['resume_script_sha256'], 'Resume script changed')
    if 'route_resume_script_sha256' in status:
        require(sha(ROOT / 'route-resume-20261024.tcl') == status['route_resume_script_sha256'], 'Route resume script changed')
        require(sha(ROOT / 'implementation/source_placed.dcp') == status['route_resume_checkpoint_sha256'], 'Placed checkpoint changed')
    handoff = json.loads((ROOT / 'handoff-audit.json').read_text())
    require(handoff['passed'], 'Source handoff failed')
    for name, digest in handoff['source_sha256'].items():
        require(sha(name) == digest, 'Handoff changed: ' + name)
    audit_log = (out / 'vivado.log').read_text()
    require(re.search(r'^AURA_VISUAL_SERVO_FINAL_PROPERTIES_VERIFIED$', audit_log, re.M) is not None, 'Independent audit incomplete')
    audit_inputs = json.loads((ROOT / 'audit-input-pins.json').read_text())
    for name, digest in audit_inputs['sha256'].items():
        require(sha(name) == digest, 'Audit artifact changed: ' + name)
    reports = verify_reports(out)
    implementation_reports = verify_reports(ROOT / 'implementation')
    require(reports['timing'] == implementation_reports['timing'], 'Independent timing differs')
    implementation = ROOT / 'implementation'
    xsa = implementation / 'visual_servo_source_implemented.xsa'
    bit = implementation / 'visual_servo_source.bit'
    original_bit = bit
    with zipfile.ZipFile(xsa) as archive:
        hwh_name, = [n for n in archive.namelist() if Path(n).name == 'kv260_ispMipiRx_vcu_DP.hwh']
        require(archive.read(hwh_name) == Path(handoff['generated_hwh']).read_bytes(), 'XSA HWH mismatch')
        embedded_bit, = [n for n in archive.namelist() if n.endswith('.bit')]
        embedded_data = archive.read(embedded_bit)
        pairing = check_pairing(bit.read_bytes(), embedded_data)
    # Exporting XSA can regenerate an identical configuration with a later
    # header timestamp. Preserve both originals; package the exact XSA bytes.
    bit = implementation / 'visual_servo_paired.bit'
    if bit.exists():
        require(bit.read_bytes() == embedded_data, 'Existing paired bitstream changed')
    else:
        with bit.open('xb') as stream:
            stream.write(embedded_data)
    require(sha(bit) == pairing['embedded_sha256'], 'Canonical bitstream/XSA mismatch')
    save(ROOT / 'bitstream-pairing-verified.json', pairing)
    require(not (ROOT / 'bundle').exists(), 'A complete bundle already exists; refuse overwrite')
    bundle = ROOT / ('bundle-staging-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    runtime = bundle / 'lib/firmware/xilinx' / APP
    runtime.mkdir(parents=True)
    driver = bundle / 'driver'
    driver.mkdir()
    commands = []

    def run(label, argv, env=None):
        process = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out / (label + '.stdout')).write_bytes(process.stdout)
        (out / (label + '.stderr')).write_bytes(process.stderr)
        commands.append({'label': label, 'returncode': process.returncode})
        require(process.returncode == 0, label + ' failed: ' + process.stderr.decode(errors='replace')[-1000:])
        return process.stdout

    bif = ROOT / 'full-pl.bif'
    bif.write_text('all:\n{\n [destination_device=pl] ' + str(bit) + '\n}\n')
    binary = runtime / (APP + '.bit.bin')
    run('bootgen', [TOOLS / 'bootgen', '-arch', 'zynqmp', '-image', bif, '-o', binary])
    baseline_binary = Path('/home/ghmd/kv260-dpu41-control-20261001/evidence/baseline-kv260-benchmark-b4096.bit.bin')
    require(binary.read_bytes()[:64] == baseline_binary.read_bytes()[:64], 'Bitstream binary header mismatch')
    overlay = runtime / (APP + '.dtbo')
    original = M3 / 'provenance/baseline-kv260-benchmark-b4096.dtbo'
    shutil.copy2(original, overlay)
    run('firmware-name', [FDT / 'fdtput', '-t', 's', overlay, '/fragment@0/__overlay__', 'firmware-name', APP + '.bit.bin'])
    old_dt = run('old-overlay', [TOOLS / 'dtc', '-I', 'dtb', '-O', 'dts', original])
    new_dt = run('new-overlay', [TOOLS / 'dtc', '-I', 'dtb', '-O', 'dts', overlay])
    require(old_dt.replace(b'kv260-benchmark-b4096.bit.bin', (APP + '.bit.bin').encode()) == new_dt, 'Unexpected overlay change')
    base_record = json.loads((PARENT / 'CURRENT_BOARD_DT.json').read_text())
    base = Path(base_record['path'])
    require(sha(base) == base_record['sha256'], 'Historical DT base changed')
    merged = out / 'historical-base-merged.dtb'
    run('merge-historical-dt', [DTC / 'fdtoverlay', '-i', base, '-o', merged, overlay],
        dict(os.environ, LD_LIBRARY_PATH=str(DTC / 'libfdt')))
    merged_dt = run('read-merged-dt', [TOOLS / 'dtc', '-I', 'dtb', '-O', 'dts', merged])
    require(not any(x in merged_dt for x in [b'xlnx,i2s', b'xlnx,audio-formatter', b'i2s_receiver', b'i2s_transmitter']), 'Retired audio DT nodes present')
    xclbin = runtime / (APP + '.xclbin')
    shutil.copy2(M3 / 'lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin', xclbin)
    require(sha(xclbin) == '875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3', 'Inherited DPU metadata mismatch')
    (runtime / 'shell.json').write_text(json.dumps({'shell_type': 'XRT_FLAT', 'num_slots': '1'}) + '\n')
    shutil.copy2(ROOT / 'validation/native/libvsrv2.so', driver / 'libvsrv.so')
    for name in ['vsrv_transport.py', 'vsrv_driver.py']:
        shutil.copy2(ROOT / 'candidate/runtime/aura/board/motion' / name, driver / name)
    native = json.loads((ROOT / 'validation/native/native-build.json').read_text())
    require(sha(driver / 'libvsrv.so') == native['library_sha256'], 'Native library pairing mismatch')
    require(int.from_bytes((driver / 'libvsrv.so').read_bytes()[18:20], 'little') == 183, 'Library is not AArch64')
    manifest = {'schema_version': 1, 'status': 'OFFLINE_VSRV2_BUNDLE_PENDING_BOARD',
                'abi': 2, 'build_id': 0x778d2512, 'app': APP, 'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'board_accessed': False, 'new_firmware_loaded': False, 'movement_commands_sent': 0,
                'joint_implementation_passed': True, 'independent_checkpoint_audit_passed': True,
                'external_waveform_verified': False, 'physical_servo_response_verified': False,
                'dpu_coexistence_verified': False, 'current_board_dt_verified': False, 'deployable': False,
                'bitstream_and_handoff_from_same_project': True, 'xsa_embedded_bitstream_matches': True,
                'historical_dt_merge_passed': True, 'historical_dt_base_boot': base_record['boot_id'],
                'historical_dt_base_sha256': base_record['sha256'], 'report': reports,
                'source_bitstream_sha256': sha(bit), 'xsa_sha256': sha(xsa),
                'original_write_bitstream_sha256': sha(original_bit),
                'bitstream_pairing': pairing,
                'source_routed_checkpoint_sha256': sha(implementation / 'source_routed.dcp'),
                'audit_input_pins': audit_inputs,
                'independent_report_sha256': {p.name: sha(p) for p in out.iterdir() if p.suffix in {'.rpt', '.tsv'}},
                'retained_dpu_xrt_metadata_sha256': sha(xclbin),
                'payload_files': {p.name: sha(p) for p in sorted(driver.iterdir())},
                'runtime_files': {'/lib/firmware/xilinx/' + APP + '/' + p.name: sha(p) for p in sorted(runtime.iterdir())},
                'commands': commands,
                'remaining': ['Coordinate board ownership with the other terminal',
                              'Read and verify current boot, FDT, active firmware and business release',
                              'Controlled firmware/STOP/ID and real DPU coexistence check',
                              'External pin waveform with servo disconnected',
                              'Observed finite motion and mechanical calibration before enabling UI']}
    save(bundle / 'candidate-manifest.json', manifest)
    (bundle / 'SHA256SUMS').write_text(''.join(sha(p) + '  ' + str(p.relative_to(bundle)) + '\n'
        for p in sorted(bundle.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))
    bundle.rename(ROOT / 'bundle')
    bundle = ROOT / 'bundle'
    status.update(state='offline_bundle_ready_pending_board', joint_implementation_passed=True,
                  independent_checkpoint_audit_passed=True, offline_bundle_ready=True,
                  finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(), report=reports,
                  bundle_manifest_sha256=sha(bundle / 'candidate-manifest.json'))
    save(ROOT / 'STATUS.json', status)
    print(json.dumps({k: manifest[k] for k in ['status', 'joint_implementation_passed', 'deployable', 'board_accessed']}, indent=2))


if __name__ == '__main__':
    main()
