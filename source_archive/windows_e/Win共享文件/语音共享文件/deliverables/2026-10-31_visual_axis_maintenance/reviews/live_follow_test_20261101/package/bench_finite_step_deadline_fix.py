#!/usr/bin/env python3
"""Two-second controlled initialization/5us step. Default is a host-only plan."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

from bench_identity_stop import require, validated_context


def run_finite(io, device, initial_us, target_us, events, clock=time.monotonic, sleep=time.sleep):
    """No queued commands or retry after lease/context loss. Always stop on exit."""
    require(type(initial_us) is int and type(target_us) is int and 1400 <= initial_us <= 1600
            and 1400 <= target_us <= 1600 and 0 < abs(target_us - initial_us) <= 5, 'Invalid finite step')
    session = int.from_bytes(os.urandom(4), 'big') or 1
    before = device.status()
    require(before['flags'] == 0 and before['lease_left_ms'] == 0, 'Output must already be stopped')
    require(before['epoch'] < 0xffffffff, 'Epoch exhausted')
    epoch = before['epoch'] + 1
    final = None
    try:
        device.stop()
        io.write(0x10, session)
        io.write(0x14, epoch)
        io.write(0x24, 0x42494e44)  # BIND
        state = device.status()
        require(state['flags'] == 8 and state['session'] == session and state['epoch'] == epoch
                and state['ack_seq'] == 0, 'BIND not confirmed')
        io.write(0x3c, initial_us)
        io.write(0x24, 0x52454621)  # REFERENCE: initialization point, not a measured angle.
        state = device.status()
        require(state['flags'] == 12 and state['width_us'] == initial_us
                and state['reference_us'] == initial_us, 'Initialization reference not confirmed')
        io.write(0x24, 0x41524d21)  # ARM; COMMIT below is the only output trigger.
        require(device.status()['flags'] == 14, 'ARM not confirmed')
        start = clock()
        seq = 0
        for index, target in enumerate((initial_us, target_us)):
            end = start + index + 1
            count = 0
            while clock() < end:
                submitted = clock()
                # Do not start shadow writes when the phase cannot contain the
                # existing 25ms submission allowance. Keep the original phase
                # deadline and lease; wait out only the bounded remainder.
                if end - submitted <= .025:
                    sleep(max(0., end - submitted))
                    break
                state = device.status()
                require(state['session'] == session and state['epoch'] == epoch
                        and state['ack_seq'] == seq and state['flags'] & 14 == 14
                        and state['reason'] == 0, 'Lease or command context lost; no retry')
                seq += 1
                io.write(0x18, seq)
                io.write(0x1c, target)
                io.write(0x20, 100)
                now = clock()
                require(0 <= now - submitted <= .025 and now < end, 'Late submission refused')
                io.write(0x24, 0x434d5421)  # COMMIT
                state = device.status()
                require(state['active'] and state['reason'] == 0 and state['ack_seq'] == seq
                        and state['target_us'] == target and state['session'] == session
                        and state['epoch'] == epoch, 'Command ACK mismatch')
                events.append({'elapsed_ms': (clock() - start) * 1000, 'target_us': target,
                               'width_us': state['width_us'], 'ack_seq': seq})
                count += 1
                sleep(min(.04, max(0, end - clock())))
            state = device.status()
            require(count >= 2 and state['active'] and state['width_us'] == target,
                    'Finite stage incomplete; no retry')
        final = device.finish()
        require(final['flags'] == 0 and final['lease_left_ms'] == 0, 'Full-pulse finish not confirmed')
    finally:
        stopped = device.stop()
        require(stopped['flags'] == 0 and stopped['lease_left_ms'] == 0, 'Final STOP not confirmed')
    return {'initial': before, 'finish': final, 'stopped': stopped, 'initialized_us': initial_us,
            'last_commanded_us': target_us, 'mechanical_reference_calibrated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--confirmation')
    parser.add_argument('--initial-us', type=int)
    parser.add_argument('--target-us', type=int)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'mode': 'PLAN_ONLY', 'board_accessed': False, 'duration_s': 2,
            'maximum_step_us': 5, 'lease_ms': 100, 'automatic_following': False,
            'initial_pulse_requires_operator_selection': True,
            'initialization_may_move_from_unknown_actual_position': True,
            'external_waveform_verified': False, 'output_on_exit': 'QUIESCE then final STOP'}))
        return
    require(args.confirmation == 'OBSERVED_FINITE_2S', 'Observed finite bench confirmation required')
    require(args.initial_us is not None and args.target_us is not None
            and 1400 <= args.initial_us <= 1600 and 1400 <= args.target_us <= 1600
            and 0 < abs(args.target_us - args.initial_us) <= 5, 'Explicit near-reference pulses required')
    driver_root, manifest, boot = validated_context(args)
    report = {'boot_id': boot, 'board_accessed': True, 'physical_output_requested': True,
        'external_waveform_verified': False, 'physical_motion_verified': False,
        'mechanical_observation': 'PENDING_USER', 'automatic_following': False,
        'events': [], 'status': 'STARTING'}
    with args.output.open('x') as output:
        try:
            sys.path.insert(0, str(driver_root))
            from vsrv_driver import VSRVDriver
            from vsrv_transport import NativeRegisters
            with NativeRegisters(driver_root / 'libvsrv.so', manifest['payload_files']['libvsrv.so'],
                                 boot, manifest['runtime_files']) as io:
                device = VSRVDriver(io, 0x10282601, boot)
                report['result'] = run_finite(io, device, args.initial_us, args.target_us, report['events'])
            report['status'] = 'FINITE_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
        except BaseException as error:
            report.update(status='FAILED_NO_AUTOMATIC_RETRY', error_type=type(error).__name__, error=str(error))
            raise
        finally:
            json.dump(report, output, indent=2)
            output.write('\n')
    print(json.dumps({'status': report['status'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
