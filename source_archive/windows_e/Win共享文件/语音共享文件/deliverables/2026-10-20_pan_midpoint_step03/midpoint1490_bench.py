"""Finite midpoint step bench: default prints a plan, never opens hardware.

1520 us is an initialization test point, not a measured mechanical reference.
This tool cannot start camera following or install a boot service.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

BOOT = '3e1add36-b917-4289-91dc-699348528782'
ROOT = Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
PLAN = {'kind': 'MIDPOINT_SINGLE_STEP_BENCH', 'initial_pulse_us': 1520,
        'stages': [{'duration_s': .5, 'target_us': pulse} for pulse in (1500, 1500, 1500, 1500, 1490, 1490, 1490, 1490)],
        'lease_ms': 100, 'duration_s': 4, 'automatic_following': False,
        'mechanical_reference_calibrated': False,
        'requires': 'Bounded reverse calibration via 1500us to 1490us with hardware slew limit',
        'output_on_exit': 'STOP; independent 100ms hardware lease if process disappears'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--confirmation', choices=['MIDPOINT1490-4S'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(dict(PLAN, status='PLAN_ONLY_NO_HARDWARE_OPENED'), ensure_ascii=False, indent=2))
        return
    if args.confirmation != 'MIDPOINT1490-4S' or args.output is None:
        parser.error('Execution requires confirmed initial movement clearance and a new output file')
    import os
    assert os.uname().machine == 'aarch64' and os.geteuid() == 0
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest() == '501cf86ec839373df57862f829d34c8b5ab90a0eeeb6db0ac679bce831899929'
    assert hashlib.sha256((ROOT/'common.py').read_bytes()).hexdigest() == 'f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
    sys.path.insert(0, str(ROOT))
    import common
    common.BOOT = BOOT
    common.guard()
    common.check_runtime()
    assert common.active() == [common.APP] and common.firmware() == common.APP+'.bit.bin'
    from vsrv_driver import VSRVDriver, BIND, REFERENCE, ARM, COMMIT
    result = {'plan': PLAN, 'boot_id': BOOT, 'physical_actuation': True,
              'user_clearance_confirmation': args.confirmation,
              'external_waveform_verified': False, 'mechanical_response': 'REQUIRES_USER_OBSERVATION',
              'events': []}
    # Exclusive-create the evidence before any output permission is set.
    with args.output.open('x') as log:
        with common.open_registers() as io:
            driver = VSRVDriver(io, 0x14da0e60, BOOT)
            try:
                initial = driver.status()
                assert (initial['flags'] == 0 and initial['lease_left_ms'] == 0
                        and initial['ack_seq'] == 46 and initial['epoch'] == 2 and initial['width_us'] == 1520
                        and initial['reference_us'] == 1504 and initial['target_us'] == 1520)
                driver.stop()
                session, epoch = 0x20261020, 3
                io.write(0x10, session)
                io.write(0x14, epoch)
                io.write(0x24, BIND)
                state = driver.status()
                assert state['flags'] == 8 and state['session'] == session and state['epoch'] == epoch
                io.write(0x3c, 1520)
                io.write(0x24, REFERENCE)
                state = driver.status()
                assert state['flags'] == 12 and state['reference_us'] == 1520 and state['width_us'] == 1520
                io.write(0x24, ARM)
                state = driver.status()
                assert state['flags'] == 14 and not state['active']
                seq = 0
                start = time.monotonic()
                for stage_index, stage in enumerate(PLAN['stages']):
                    stage_end = start+(stage_index+1)*stage['duration_s']
                    stage_commands = 0
                    while time.monotonic() < stage_end:
                        seq += 1
                        target = stage['target_us']
                        io.write(0x18, seq)
                        io.write(0x1c, target)
                        io.write(0x20, PLAN['lease_ms'])
                        io.write(0x24, COMMIT)
                        state = driver.status()
                        assert (state['active'] and state['reason'] == 0 and state['ack_seq'] == seq
                                and state['target_us'] == target and state['session'] == session and state['epoch'] == epoch)
                        result['events'].append({'elapsed_ms': round((time.monotonic()-start)*1000, 2),
                                                 'target_us': target, 'status': state})
                        stage_commands += 1
                        time.sleep(.04)
                    state = driver.status()
                    assert stage_commands >= 2 and state['active'] and state['width_us'] == stage['target_us']
                result['status'] = 'FINITE_BENCH_ACK_PASS_MECHANICAL_OBSERVATION_PENDING'
            except BaseException as exc:
                result['status'] = 'FAILED'
                result['error'] = type(exc).__name__+': '+str(exc)
                raise
            finally:
                try:
                    result['final'] = driver.stop()
                except BaseException as exc:
                    result['stop_error'] = type(exc).__name__+': '+str(exc)
                    raise
                finally:
                    log.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
                    log.flush()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
