"""Attended fixed-trajectory entry. Default and --check never open MMIO."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import sys
import time
import urllib.request

from reference_receipt import validate_receipt, same_stopped_readback

R = Path('/home/root/aura-pan-current-20261024/da36c36a')
G = Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1')
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
P = OPS / 'pan-face-edge-v5/continuous-v10r15'
OLD = Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
HERE = Path(__file__).resolve().parent
BOOT = 'da36c36a-ef4d-4122-8ad6-cfae3931303e'
FDT = '55805463ec5f0411e3797902b9994d3ff12482545130da518a99ad7712a23914'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def get(port, path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=3) as response:
        return json.load(response)


def preflight(package_sha):
    if platform.machine() != 'aarch64' or os.geteuid() != 0:
        raise RuntimeError('BOARD_CHECK_ONLY_ON_KV260')
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert sha('/sys/firmware/fdt') == FDT
    assert sha(HERE / 'package-manifest.json') == package_sha
    package = json.loads((HERE / 'package-manifest.json').read_text())
    assert all('/' not in n and not (HERE / n).is_symlink() and sha(HERE / n) == h
               for n, h in package['files'].items())
    assert sha(P / 'deployment-manifest.json') == 'c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de'
    control = json.loads((P / 'deployment-manifest.json').read_text())
    assert all(sha(x['destination']) == x['sha256'] for x in control['files'])
    assert sha(OLD / 'candidate-manifest.json') == 'ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
    manifest = json.loads((OLD / 'candidate-manifest.json').read_text())
    assert all(sha(p) == h for p, h in manifest['runtime_files'].items())
    assert all(sha(OLD / 'driver' / p) == h for p, h in manifest['payload_files'].items())
    firmware = Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
    assert firmware == 'aura-visual-servo-b4096-v2.bit.bin'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating'
    assert Path('/etc/vart.conf').read_text() == 'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-v2/aura-visual-servo-b4096-v2.xclbin\n'
    assert sha(G / 'startup/config.json') == 'd12af30e70b75be8fd54d6d030e3b98a9df204bacb803fbf6fc5914e9f391594'
    gui = json.loads((G / 'startup/config.json').read_text())
    assert all(sha(G / 'runtime/aura' / p) == h for p, h in gui['component_sha256'].items())
    h, u = get(8790, '/health'), get(8783, '/api/state')
    m = u['manual_pan']
    assert h['pid'] == 54394 and not h['dpu_schedule']['owner_fenced']
    assert m['state'] == 'FAULT' and not m['automatic_following'] and m.get('readback') is None
    assert u['phase'] == 'IDLE' and not u.get('playing')
    return manifest, control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--package-sha256')
    parser.add_argument('--reference-sha256')
    args = parser.parse_args()
    if not args.check and not args.execute:
        print(json.dumps(dict(mode='PLAN_ONLY', board_accessed=False, MMIO_opened=False,
                              reference_us=1420, excursion_us=-5, maximum_duration_s=2,
                              requires='current observed reference, pinned receipt, stopped readback and exclusive transport')))
        return
    manifest, control = preflight(args.package_sha256)
    reference_path = R / 'attended-fixed-reference.json'
    if not reference_path.is_file():
        if args.execute:
            raise RuntimeError('CURRENT_USER_REFERENCE_MISSING_NO_MMIO')
        print(json.dumps(dict(status='FILES_AND_SERVICES_PASS_AWAITING_CURRENT_REFERENCE',
                              boot_id=BOOT, MMIO_opened=False, motor_commands=0, physical_test_ready=False)))
        return
    assert not reference_path.is_symlink() and sha(reference_path) == args.reference_sha256
    receipt = validate_receipt(json.loads(reference_path.read_text()), boot_id=BOOT, fdt_sha256=FDT, now=time.monotonic())
    if not args.execute:
        print(json.dumps(dict(status='REFERENCE_FILE_PASS_REGISTERS_NOT_OPENED', boot_id=BOOT,
                              MMIO_opened=False, motor_commands=0, physical_test_ready=False)))
        return
    sys.path[:0] = [str(HERE), str(P), str(OLD / 'driver')]
    from batch_transport import BatchRegisters
    from vsrv_driver import PhysicalReference
    from fixed_bench_adapter import FixedBenchDriver
    from run_fixed_motion import BenchPermit, BenchFailure, plan_digest, run_fixed_motion
    plans = json.loads((HERE / 'plans.json').read_text())
    rows = next(x['samples'] for x in plans['cases'] if x['direction_in_pulse_space'] == -1)
    reference = PhysicalReference(BOOT, 1420, receipt['authorization_id'], receipt['user_observation'], 1, True, True)
    permit = BenchPermit(BOOT, receipt['authorization_id'], receipt['authorization_id'], 1420, 1402, 1420,
                         secrets.randbelow(0xfffffffe) + 1, receipt['observed_mono_s'], receipt['expires_mono_s'], plan_digest(rows))
    report_path = R / ('fixed-trajectory-' + receipt['authorization_id'] + '.json')
    io = driver = None
    report = dict(status='STARTING', boot_id=BOOT, physical_motion_verified=False,
                  reference_receipt_sha256=sha(reference_path), package_sha256=args.package_sha256)
    failure = None
    with (OPS / 'operation.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        preflight(args.package_sha256)
        assert sha(reference_path) == args.reference_sha256
        validate_receipt(receipt, boot_id=BOOT, fdt_sha256=FDT, now=time.monotonic())
        with report_path.open('x') as out:
            try:
                library = P / 'libvsrv_batch.so'
                pin = next(x['sha256'] for x in control['files'] if x['destination'] == str(library))
                io = BatchRegisters(library, pin, BOOT, manifest['runtime_files'])
                driver = FixedBenchDriver(io, 0x778d2512, BOOT, minimum_us=1402, maximum_us=1420)
                assert same_stopped_readback(receipt, driver.status()), 'CURRENT_STOPPED_REFERENCE_CHANGED'
                report['result'] = run_fixed_motion(driver, reference, permit, rows)
                report['status'] = 'FIXED_TRAJECTORY_STOPPED_OBSERVATION_PENDING'
            except BaseException as error:
                failure = error
                report.update(status='FAILED_NO_AUTOMATIC_RETRY', error_type=type(error).__name__, error=str(error))
                if isinstance(error, BenchFailure):
                    report['result'] = error.report
            finally:
                if driver is not None and driver.last_failure is not None:
                    report['adapter_failure'] = driver.last_failure
                if io is not None:
                    try:
                        io.close()
                    except BaseException as error:
                        report.update(status='FAILED_NO_AUTOMATIC_RETRY', transport_close_error=type(error).__name__ + ': ' + str(error))
                        if failure is None:
                            failure = error
                json.dump(report, out, indent=2)
                out.write('\n')
    print(json.dumps(dict(status=report['status'], report=str(report_path), physical_observation_pending=True)))
    if failure is not None:
        raise failure


if __name__ == '__main__':
    main()
