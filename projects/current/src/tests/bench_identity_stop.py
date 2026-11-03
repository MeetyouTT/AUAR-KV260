#!/usr/bin/env python3
"""Explicit VSRV/2 ID/STOP bench only. Default prints a plan; it never arms."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

APP = 'aura-visual-servo-b4096-wide-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validated_context(args):
    """Validate the pinned controlled-bench context, without opening MMIO."""
    require(platform.machine() == 'aarch64' and os.geteuid() == 0, 'KV260 root-only bench; host execution refused')
    require(all([args.manifest, args.manifest_sha256, args.context, args.output]), 'All pinned context arguments required')
    require(sha(args.manifest) == args.manifest_sha256, 'Candidate manifest changed')
    manifest = json.loads(args.manifest.read_text())
    require(manifest.get('status') == 'OFFLINE_VSRV2_BUNDLE_PENDING_BOARD'
        and manifest.get('app') == APP and manifest.get('abi') == 2
        and manifest.get('build_id') == 0x10282601
        and manifest.get('joint_implementation_passed') is True
        and manifest.get('independent_checkpoint_audit_passed') is True, 'Wrong or incomplete candidate')
    context = json.loads(args.context.read_text())
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(boot == context['boot_id'], 'Boot changed after inspection')
    require(sha(Path('/sys/firmware/fdt')) == context['fdt_sha256'], 'FDT changed after inspection')
    firmware = Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
    require(firmware == context['firmware_name'] == APP + '.bit.bin', 'Candidate firmware not active')
    require(Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating', 'FPGA not operating')
    require(Path('/etc/vart.conf').read_text() == 'firmware: /lib/firmware/xilinx/' + APP + '/' + APP + '.xclbin\n', 'VART firmware mismatch')
    root = args.manifest.resolve().parent
    driver = root / 'driver'
    require(set(manifest['payload_files']) == {'libvsrv.so', 'vsrv_driver.py', 'vsrv_transport.py'}, 'Driver payload differs')
    for name, digest in manifest['payload_files'].items():
        require(sha(driver / name) == digest, 'Driver payload changed: ' + name)
    expected_runtime = {'/lib/firmware/xilinx/' + APP + '/' + APP + ext for ext in ['.bit.bin', '.dtbo', '.xclbin']}
    require(expected_runtime.issubset(manifest['runtime_files']), 'Incomplete firmware pins')
    for name, digest in manifest['runtime_files'].items():
        require(sha(Path(name)) == digest, 'Installed firmware changed: ' + name)
    return driver, manifest, boot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--confirmation')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'mode': 'PLAN_ONLY', 'app': APP, 'abi': 2, 'build_id': '0x10282601',
            'register_commands': ['STOP'], 'ARM': False, 'COMMIT': False, 'waveform_test': False,
            'board_accessed': False, 'requires': ['coordinated board window', 'new firmware loaded',
                'fresh board context', 'pinned offline manifest', 'explicit ID_STOP_ONLY confirmation']}))
        return 0
    require(args.confirmation == 'ID_STOP_ONLY', 'Explicit ID_STOP_ONLY confirmation required; no MMIO')
    driver, manifest, boot = validated_context(args)
    # Reserve a new result before opening the target library or MMIO.
    with args.output.open('x') as result_file:
        report = {'boot_id': boot, 'manifest_sha256': args.manifest_sha256,
            'board_accessed': True, 'firmware_modified': False, 'services_modified': False,
            'ARM_sent': False, 'COMMIT_sent': False, 'BIND_sent': False, 'REFERENCE_sent': False,
            'identity_stop_passed': False, 'external_waveform_verified': False,
            'physical_motion_verified': False, 'dpu_coexistence_verified': False}
        try:
            sys.path.insert(0, str(driver))
            from vsrv_driver import VSRVDriver
            from vsrv_transport import NativeRegisters
            # NativeRegisters takes the exclusive motion flock before MMIO.
            with NativeRegisters(driver / 'libvsrv.so', manifest['payload_files']['libvsrv.so'],
                                 boot, manifest['runtime_files']) as registers:
                device = VSRVDriver(registers, 0x10282601, boot)
                report['before'] = device.status()
                started = time.monotonic()
                report['after_stop'] = device.stop()
                report['stop_api_wall_ms'] = (time.monotonic() - started) * 1000
                require(report['after_stop']['flags'] == 0 and report['after_stop']['lease_left_ms'] == 0, 'STOP not confirmed')
            # Successful context-manager close also confirms the final STOP.
            report['identity_stop_passed'] = True
        except BaseException as error:
            report['error_type'] = type(error).__name__
            report['error'] = str(error)
            raise
        finally:
            json.dump(report, result_file, indent=2)
            result_file.write('\n')
    print(json.dumps({'identity_stop_passed': True, 'motion_tested': False, 'report': str(args.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
