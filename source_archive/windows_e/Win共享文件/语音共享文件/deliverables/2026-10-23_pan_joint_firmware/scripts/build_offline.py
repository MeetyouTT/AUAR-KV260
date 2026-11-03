#!/usr/bin/env python3
"""Rebuild the VSRV/2 source platform in isolation; no board I/O."""
import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
PARENT = Path('/home/ghmd/kv260-visual-servo-20261007')
CANDIDATE = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_safe_completion')
SETTINGS = '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh'
BUILD_ID = '0x778d2512'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    with (ROOT / '.build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.nice(15)
        platform = ROOT / 'platform'
        implementation = ROOT / 'implementation'
        platform.mkdir()
        implementation.mkdir()
        snapshot = ROOT / 'candidate'
        snapshot.mkdir()
        for name in ['rtl', 'native', 'runtime', 'tests', 'config', 'scripts']:
            shutil.copytree(CANDIDATE / name, snapshot / name)
        # Check every frozen candidate payload before using it.
        verified = json.loads((CANDIDATE / 'verification.json').read_text())
        for row in verified['files']:
            path = CANDIDATE / row['path']
            if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
                raise RuntimeError('Frozen candidate changed: ' + row['path'])
        build_match = re.search(r"BUILD_ID=32'h([0-9a-fA-F]+)", (snapshot / 'rtl/visual_servo.sv').read_text())
        if not build_match or int(build_match[1], 16) != int(BUILD_ID, 16):
            raise RuntimeError('Candidate RTL build ID mismatch')
        parent = json.loads((PARENT / 'CURRENT_SOURCE_PLATFORM.json').read_text())
        audit = json.loads((PARENT / 'CURRENT_SOURCE_FINAL_AUDIT.json').read_text())
        for name, expected in parent['source_sha256'].items():
            if sha(name) != expected:
                raise RuntimeError('Parent source changed: ' + name)
        ref = Path(audit['implementation']) / 'source_routed.dcp'
        if sha(ref) != audit['input_sha256'][str(ref)]:
            raise RuntimeError('Parent routed checkpoint changed')
        spec = importlib.util.spec_from_file_location('historic_source_builder', PARENT / 'scripts/prepare_source_platform.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        (platform / 'inputs/bd').mkdir(parents=True)
        shutil.copy2(helper.BD, platform / 'inputs/bd' / helper.BD.name)
        shutil.copytree(helper.BD.parent / 'ip', platform / 'inputs/bd/ip')
        xdc = re.sub(r'\blrclk_tx\b', 'servo_pwm', helper.XDC.read_text())
        xdc = xdc.replace('DRIVE 4 [get_ports servo_pwm]', 'DRIVE 8 [get_ports servo_pwm]')
        if 'DRIVE 8 [get_ports servo_pwm]' not in xdc:
            raise RuntimeError('PWM drive constraint not found')
        (platform / 'pin.xdc').write_text(xdc)
        shutil.copy2(snapshot / 'rtl/visual_servo.sv', platform / 'visual_servo.sv')
        (platform / 'disabled_audio.sv').write_text(helper.annotated_audio((helper.ADAPT / 'fpga/rtl/disabled_audio.sv').read_text()))
        old_stage = Path(parent['evidence'])
        shutil.copy2(old_stage / 'repos.txt', platform / 'repos.txt')
        shutil.copytree(old_stage / 'ip_cache', platform / 'ip_cache')
        prepare = (PARENT / 'scripts/prepare_source_platform.tcl').read_text()
        (ROOT / 'prepare.tcl').write_text('set_param general.maxThreads 1\n' + prepare)
        implement = (PARENT / 'scripts/implement_source_platform.tcl').read_text()
        implement = implement.replace('general.maxThreads 4', 'general.maxThreads 1').replace('synth_1 -jobs 4', 'synth_1 -jobs 1')
        # Export the exact implemented bitstream together with its hardware metadata.
        implement = implement.replace('write_hw_platform -fixed ', 'write_hw_platform -fixed -include_bit ')
        implement = implement.replace('write_bitstream [', 'write_bitstream -bin_file [')
        (ROOT / 'implement.tcl').write_text(implement)
        sources = [snapshot / 'rtl/visual_servo.sv', snapshot / 'native/vsrv_protocol.h',
                   ROOT / 'prepare.tcl', ROOT / 'implement.tcl', Path(__file__),
                   helper.BD, helper.XDC, platform / 'pin.xdc', platform / 'disabled_audio.sv']
        pins = {str(p): sha(p) for p in sources}
        status = {'state': 'prepared', 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'abi': 2, 'build_id': BUILD_ID, 'threads': 1, 'jobs': 1,
                  'niceness': os.getpriority(os.PRIO_PROCESS, 0),
                  'source_sha256': pins, 'reference': str(ref), 'reference_sha256': sha(ref),
                  'board_accessed': False, 'firmware_loaded': False, 'movement_commands_sent': 0,
                  'joint_implementation_passed': False, 'external_waveform_verified': False,
                  'physical_motion_verified': False, 'deployable': False}
        write_json(ROOT / 'STATUS.json', status)
        if args.prepare_only:
            print(json.dumps(status, ensure_ascii=False), flush=True)
            return
        env = dict(os.environ, AURA_PLATFORM_OUT=str(platform),
                   AURA_PLATFORM_BUILD_ID=str(int(BUILD_ID, 16)),
                   AURA_SOURCE_IMPL_OUT=str(implementation), AURA_SOURCE_IMPL_REFERENCE=str(ref),
                   OMP_NUM_THREADS='1')
        for stage, marker in [('prepare', 'AURA_SOURCE_PLATFORM_GENERATED'),
                              ('implement', 'AURA_SOURCE_PLATFORM_IMPLEMENTED')]:
            status['state'] = stage + '_running'
            write_json(ROOT / 'STATUS.json', status)
            argv = ['bash', '--noprofile', '--norc', '-c',
                    'source "$1"; exec vivado -mode batch -source "$2" -log "$3" -journal "$4"',
                    'aura-pan-offline', SETTINGS, str(ROOT / (stage + '.tcl')),
                    str(ROOT / (stage + '.log')), str(ROOT / (stage + '.jou'))]
            with (ROOT / (stage + '-console.txt')).open('wb') as log:
                process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                status['pid'] = process.pid
                write_json(ROOT / 'STATUS.json', status)
                rc = process.wait()
            changed = [name for name, expected in pins.items() if sha(name) != expected]
            status[stage + '_rc'] = rc
            status['changed_inputs'] = changed
            if rc or changed or marker not in (ROOT / (stage + '-console.txt')).read_text(errors='replace'):
                status['state'] = stage + '_failed'
                write_json(ROOT / 'STATUS.json', status)
                raise RuntimeError('Offline ' + stage + ' failed; see its console log')
            status[stage + '_passed'] = True
        status.update(state='implemented_pending_audit', joint_implementation_passed=True,
                      finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        write_json(ROOT / 'STATUS.json', status)
        print(json.dumps({k: status[k] for k in ['state', 'abi', 'build_id', 'board_accessed', 'deployable']}), flush=True)


if __name__ == '__main__':
    main()
