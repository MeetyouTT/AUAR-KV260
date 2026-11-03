"""Injected bounded bench core. CLI is PLAN_ONLY; no hardware adapter is provided.

An adapter MUST already own and validate the real transport, current boot,
identity, physical reference and operator authorization. BenchPermit describes
that contract; constructing this dataclass is NOT evidence of authorization.
submit_bench has its own finite bench deadline, never a synthetic face stamp.
The existing native final-write race is not solved by this Python core.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import time

from plan_fixed import LIMITS, make_plan

DURATION_S = 5.
TICK_S = .02
FINISH_RESERVE_S = .04
MIN_SUBMISSION_INTERVAL_S = .02
LEASE_MS = 100
MARGIN_MS = 20


@dataclass(frozen=True)
class BenchPermit:
    boot_id: str
    authorization_id: str
    observation_id: str
    reference_us: int
    minimum_us: int
    maximum_us: int
    session: int
    valid_from_mono_s: float
    valid_until_mono_s: float
    plan_sha256: str


class BenchFailure(RuntimeError):
    def __init__(self, reason, report):
        super().__init__(reason)
        self.report = report


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def plan_digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_plan(rows, permit):
    require(type(permit.reference_us) is int and type(permit.minimum_us) is int and type(permit.maximum_us) is int,
            'INTEGER_REFERENCE_AND_WINDOW_REQUIRED')
    require(1400 <= permit.minimum_us < permit.maximum_us <= 1600
            and permit.maximum_us - permit.minimum_us <= 20, 'APPROVED_NARROW_WINDOW_REQUIRED')
    require(len(rows) == 251 and [r['time_ms'] for r in rows] == list(range(0, 5001, 20)), 'EXACT_FIVE_SECOND_PLAN_REQUIRED')
    require(plan_digest(rows) == permit.plan_sha256, 'PLAN_BINDING_MISMATCH')
    for row in rows:
        p, v, a = (row[n] for n in ('position_us', 'velocity_us_s', 'acceleration_us_s2'))
        require(all(type(x) in (int, float) and math.isfinite(x) for x in (p, v, a)), 'NONFINITE_TRAJECTORY')
        require(permit.minimum_us - 1e-7 <= p <= permit.maximum_us + 1e-7
                and type(row['target_us']) is int and row['target_us'] == round(p)
                and permit.minimum_us <= row['target_us'] <= permit.maximum_us, 'TRAJECTORY_OUTSIDE_APPROVED_WINDOW')
        require(abs(p - permit.reference_us) <= 15. + 1e-7, 'EXCURSION_EXCEEDS_FIFTEEN_US')
        require(abs(v) <= LIMITS['speed_us_s'] + 1e-7 and abs(a) <= LIMITS['acceleration_us_s2'] + 1e-7,
                'TRAJECTORY_RATE_LIMIT')
    for a, b in zip(rows, rows[1:]):
        require(abs(b['position_us'] - a['position_us']) <= LIMITS['speed_us_s'] * TICK_S + 1e-7
                and abs(b['target_us'] - a['target_us']) <= 1, 'TRAJECTORY_STEP_LIMIT')
        require(abs(b['acceleration_us_s2'] - a['acceleration_us_s2']) <= LIMITS['jerk_us_s3'] * TICK_S + 1e-7,
                'TRAJECTORY_JERK_LIMIT')
    for row in [rows[0], *rows[248:]]:
        require(abs(row['position_us'] - permit.reference_us) < 1e-7
                and row['target_us'] == permit.reference_us and abs(row['velocity_us_s']) < 1e-7
                and abs(row['acceleration_us_s2']) < 1e-7, 'REFERENCE_NOT_REACHED_BEFORE_FINISH_RESERVE')


def run_fixed_motion(driver, reference, permit, rows, *, clock=time.monotonic, sleep=time.sleep):
    """Run only against an explicitly supplied, independently validated adapter.

    Adapter methods: status(); confirm_and_arm(reference, session, epoch,
    authorized=True); submit_bench(target, absolute_deadline_s=...,
    maximum_lease_ms=..., margin_ms=...); finish(absolute_deadline_s=...); stop().
    An accepted submission returns outcome, observed_mono_s and readback.
    observed_mono_s is the exact sampling time, or a conservative batch-read
    end time accompanied by lease_expiry_lower_bound_mono_s. The latter proves
    remaining validity without pretending to know the individual read instant.
    No files, network, camera packets, MMIO or actuator imports occur here.
    """
    validate_plan(rows, permit)
    require(all(callable(getattr(driver, name, None)) for name in
                ('status', 'confirm_and_arm', 'submit_bench', 'finish', 'stop')), 'VALIDATED_BENCH_ADAPTER_REQUIRED')
    require(isinstance(permit.boot_id, str) and permit.boot_id and driver.boot_id == permit.boot_id
            and reference.boot_id == permit.boot_id and reference.reference_us == permit.reference_us
            and reference.confirmed is True, 'CURRENT_BOOT_OBSERVED_REFERENCE_REQUIRED')
    require(isinstance(permit.authorization_id, str) and permit.authorization_id
            and isinstance(permit.observation_id, str) and permit.observation_id, 'ATTENDED_EVIDENCE_IDENTIFIERS_REQUIRED')
    require(type(permit.session) is int and 0 < permit.session < 0xffffffff, 'EXPLICIT_SESSION_REQUIRED')
    require(all(type(x) in (int, float) and math.isfinite(x)
                for x in (permit.valid_from_mono_s, permit.valid_until_mono_s)), 'FINITE_PERMIT_TIMES_REQUIRED')
    now = clock()
    require(permit.valid_from_mono_s <= now and now + DURATION_S <= permit.valid_until_mono_s,
            'CURRENT_BENCH_WINDOW_REQUIRED')
    report = dict(status='STARTING', boot_id=permit.boot_id, authorization_id=permit.authorization_id,
                  observation_id=permit.observation_id, plan_sha256=permit.plan_sha256,
                  requested_duration_s=DURATION_S, finish_reserve_s=FINISH_RESERVE_S,
                  scheduler='LATEST_DUE_PLAN_SLOT_AFTER_PREVIOUS_ACK_PLUS_20MS',
                  maximum_submissions=248, minimum_submission_interval_s=MIN_SUBMISSION_INTERVAL_S,
                  skipped_slots_total=0,
                  physical_motion_verified=False, hardware_absolute_deadline_guaranteed=False,
                  source_kind='EXPLICIT_FINITE_BENCH_NO_FACE_PACKETS', commands=[], stop_confirmed=False,
                  initial_readback=None, finish_readback=None, stopped_readback=None, error=None, stop_error=None)
    failure = None
    try:
        before = driver.status()
        report['initial_readback'] = dict(before)
        require(before['flags'] == 0 and before['lease_left_ms'] == 0 and before['reason'] == 0
                and before['width_us'] == before['target_us'] == permit.reference_us,
                'CURRENT_STOPPED_READBACK_MUST_MATCH_OBSERVED_REFERENCE')
        require(type(before['epoch']) is int and 0 <= before['epoch'] < 0xffffffff, 'EPOCH_EXHAUSTED')
        start = clock()
        deadline = start + DURATION_S
        require(deadline <= permit.valid_until_mono_s, 'BENCH_WINDOW_EXPIRED_DURING_PREFLIGHT')
        report.update(started_mono_s=start, absolute_deadline_mono_s=deadline)
        epoch, seq = before['epoch'] + 1, 0
        target = previous_target = permit.reference_us
        last_returned = last_row = None
        last_planned_index = -1
        driver.confirm_and_arm(reference, permit.session, epoch, authorized=True)

        def check_state(state, flags, expected_seq, expected_target, previous_width):
            require(state['flags'] == flags and state['reason'] == 0
                    and state['session'] == permit.session and state['epoch'] == epoch
                    and state['ack_seq'] == expected_seq and state['target_us'] == expected_target,
                    'BENCH_LEASE_OR_ACK_CONTEXT_LOST')
            # PL can latch a newly acknowledged target on the next PWM frame.
            widths = previous_width if isinstance(previous_width, tuple) else (previous_width,)
            require(state['width_us'] in widths + (expected_target,)
                    and permit.minimum_us <= state['width_us'] <= permit.maximum_us, 'UNEXPECTED_PWM_WIDTH')
            require(state['lease_left_ms'] == 0 if flags == 14 else 0 < state['lease_left_ms'] <= LEASE_MS,
                    'INVALID_HARDWARE_LEASE')

        def wait_until(due):
            for _ in range(8):
                if clock() >= due:
                    break
                sleep(due - clock())
            require(clock() >= due, 'CLOCK_OR_SLEEP_DID_NOT_ADVANCE')
        finish_at = deadline - FINISH_RESERVE_S
        while clock() < finish_at:
            # Allow a legal slow PS call to finish. Never replay its missed
            # slots or issue the next COMMIT immediately after its ACK.
            next_eligible = start if last_returned is None else last_returned + MIN_SUBMISSION_INTERVAL_S
            if next_eligible >= finish_at - 1e-9:
                break  # No additional COMMIT fits; avoid a needless tail sleep.
            wait_until(next_eligible)
            if clock() >= finish_at:
                break
            state = driver.status()
            check_state(state, 14 if seq == 0 else 15, seq, target, previous_target)
            submitted = clock()
            if submitted >= finish_at:
                break
            require(last_returned is None or submitted - last_returned >= MIN_SUBMISSION_INTERVAL_S - 1e-9,
                    'SUBMISSION_SPACING_NO_CATCHUP')
            planned_index = math.floor((submitted - start) / TICK_S + 1e-7)
            require(last_planned_index < planned_index < 248, 'PLAN_SLOT_CLOCK_INVALID')
            require(len(report['commands']) < 248, 'SUBMISSION_COUNT_BUDGET_EXHAUSTED')
            row = rows[planned_index]
            scheduled = start + row['time_ms'] / 1000.
            require(scheduled <= submitted + 1e-9, 'FUTURE_PLAN_SLOT_REFUSED')
            require(abs(row['target_us'] - target) <= 1, 'SKIPPED_SLOT_TARGET_STEP_EXCEEDS_ONE_US')
            skipped_slots = planned_index - last_planned_index - 1
            command = dict(scheduled_mono_s=scheduled, submitted_mono_s=submitted,
                           planned_index=planned_index, skipped_slots=skipped_slots,
                           target_us=row['target_us'], absolute_deadline_mono_s=deadline)
            report['commands'].append(command)
            report['skipped_slots_total'] += skipped_slots
            ack = driver.submit_bench(row['target_us'], absolute_deadline_s=deadline,
                                      maximum_lease_ms=LEASE_MS, margin_ms=MARGIN_MS)
            received = clock()
            # The adapter may reuse its ACK dictionary. Keep scalar snapshots,
            # never references that a later submission can mutate in history.
            snapshot = {name: ack.get(name) for name in
                        ('outcome', 'reason', 'observed_mono_s', 'snapshot_started_mono_s',
                         'snapshot_timing', 'lease_expiry_lower_bound_mono_s', 'lease_expiry_upper_bound_mono_s')}
            if isinstance(ack.get('readback'), dict):
                snapshot['readback'] = {name: ack['readback'].get(name) for name in
                    ('flags', 'reason', 'ack_seq', 'session', 'epoch', 'target_us', 'width_us', 'lease_left_ms')}
            command.update(returned_mono_s=received, acknowledgement=snapshot)
            require(received < deadline, 'SUBMISSION_RETURNED_AFTER_ABSOLUTE_DEADLINE')
            require(ack.get('outcome') == 'ACCEPTED', 'BENCH_SUBMISSION_REJECTED')
            observed = ack.get('observed_mono_s')
            require(type(observed) in (int, float) and math.isfinite(observed)
                    and submitted <= observed <= received, 'ACK_SAMPLE_TIME_INVALID')
            rb = ack['readback']
            check_state(rb, 15, seq + 1, row['target_us'], (state['width_us'], target))
            expiry = observed + rb['lease_left_ms'] / 1000.
            require(received < expiry <= deadline - MARGIN_MS / 1000. + 1e-9, 'ACK_LEASE_OUTSIDE_ORIGINAL_WINDOW')
            lower = ack.get('lease_expiry_lower_bound_mono_s', expiry)
            require(type(lower) in (int, float) and math.isfinite(lower) and lower <= expiry
                    and received < lower, 'ACK_LEASE_LOWER_BOUND_EXPIRED')
            previous_target, target = target, row['target_us']
            last_returned, last_row, last_planned_index = received, row, planned_index
            seq += 1
        require(target == permit.reference_us, 'FINAL_ACCEPTED_TARGET_NOT_REFERENCE')
        require(last_row is not None and abs(last_row['position_us'] - permit.reference_us) < 1e-7
                and abs(last_row['velocity_us_s']) < 1e-7 and abs(last_row['acceleration_us_s2']) < 1e-7,
                'FINAL_ACCEPTED_PLAN_STATE_NOT_AT_REST')
        report.update(last_planned_index=last_planned_index,
                      unsubmitted_tail_slots_before_finish=247 - last_planned_index)
        state = driver.status()
        check_state(state, 15, seq, target, previous_target)
        require(clock() <= deadline - .02, 'INSUFFICIENT_FINISH_RESERVE')
        finished = driver.finish(absolute_deadline_s=deadline)
        report['finish_readback'] = dict(finished)
        require(clock() <= deadline, 'QUIESCE_RETURNED_AFTER_DEADLINE')
        require(finished['flags'] == 0 and finished['lease_left_ms'] == 0 and finished['reason'] == 0
                and finished['session'] == permit.session and finished['epoch'] == epoch
                and finished['ack_seq'] == seq and finished['target_us'] == finished['width_us'] == permit.reference_us,
                'FINAL_QUIESCE_NOT_CONFIRMED_AT_REFERENCE')
    except BaseException as exc:
        failure = exc
        report['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        try:
            stopped = driver.stop()
            report['stopped_readback'] = dict(stopped)
            require(stopped['flags'] == 0 and stopped['lease_left_ms'] == 0 and stopped['reason'] == 0,
                    'FINAL_STOP_NOT_CONFIRMED')
            report['stop_confirmed'] = True
            if failure is None:
                require(stopped['width_us'] == stopped['target_us'] == permit.reference_us, 'STOPPED_REFERENCE_MISMATCH')
                require(stopped['session'] == permit.session and stopped['epoch'] == epoch and stopped['ack_seq'] == seq,
                        'STOPPED_CONTEXT_MISMATCH')
                require(clock() <= deadline, 'FINAL_STOP_RETURNED_AFTER_DEADLINE')
        except BaseException as exc:
            report['stop_confirmed'] = False
            report['stop_error'] = dict(type=type(exc).__name__, message=str(exc))
            if failure is None:
                failure = exc
                report['error'] = dict(type=type(exc).__name__, message=str(exc))
        report['completed_mono_s'] = clock()
    if failure is not None:
        report['status'] = 'FAILED_NO_AUTOMATIC_RETRY'
        raise BenchFailure(report['error']['message'], report) from failure
    report['status'] = 'FIXED_BENCH_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--example-reference-us', type=int, default=1420)
    args = parser.parse_args()
    if args.execute:
        parser.error('EXECUTION_REFUSED: current-boot attended hardware/reference/authorization adapter is not implemented')
    rows = make_plan(args.example_reference_us, -1)
    print(json.dumps(dict(mode='PLAN_ONLY', board_accessed=False, maximum_duration_s=5,
                          sample_count=len(rows), maximum_submissions=248, finish_reserve_ms=40,
                          example_reference_is_not_current_position=True, plan_sha256=plan_digest(rows),
                          hardware_adapter_implemented=False, executable=False)))


if __name__ == '__main__':
    main()
