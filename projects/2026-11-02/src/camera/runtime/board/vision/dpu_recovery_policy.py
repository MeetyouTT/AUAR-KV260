"""Bounded recovery decisions; the scheduler holds its condition for every call."""
from collections import deque


class YuNetRecoveryPolicy:
    def __init__(self):
        self.phase = 'RUNNING'
        self.reason = None
        self.cooldown_s = 10.
        self.window_s = 600.
        self.maximum_attempts = 2
        self.required_successes = 3
        self.primary_max_age_s = .5
        self.attempt_times = deque(maxlen=self.maximum_attempts)
        self.cooldown_until = 0.
        self.fault_primary_calls = self.fault_primary_overruns = 0
        self.probe_successes = self.faults = self.attempts = self.recoveries = 0

    def fault(self, now, *, completed, body_failed, hardcap, guard,
              primary_calls, primary_overruns):
        self.faults += 1
        self.probe_successes = 0
        self.fault_primary_calls = primary_calls
        self.fault_primary_overruns = primary_overruns
        if not completed or body_failed or guard or not hardcap:
            self.phase, self.reason = 'LATCHED', 'unsafe_or_unknown_completion'
        elif len(self.attempt_times) == self.maximum_attempts and now - self.attempt_times[0] < self.window_s:
            self.phase, self.reason = 'LATCHED', 'recovery_budget_exhausted'
        else:
            self.phase, self.reason = 'COOLDOWN', 'completed_hardcap_only'
            self.cooldown_until = now + self.cooldown_s

    def due(self, now, *, primary_calls, primary_overruns, last_primary):
        if self.phase != 'COOLDOWN' or now < self.cooldown_until:
            return False
        if primary_overruns != self.fault_primary_overruns:
            self.phase, self.reason = 'LATCHED', 'primary_overrun_after_fault'
            return False
        if (primary_calls <= self.fault_primary_calls or last_primary is None
                or not 0 <= now - last_primary <= self.primary_max_age_s):
            return False
        while self.attempt_times and now - self.attempt_times[0] >= self.window_s:
            self.attempt_times.popleft()
        if len(self.attempt_times) >= self.maximum_attempts:
            self.phase, self.reason = 'LATCHED', 'recovery_budget_exhausted'
            return False
        return True

    def admitted(self, now):
        # Called only after atomic ordinary primary/deadline admission.
        self.attempt_times.append(now)
        self.attempts += 1
        self.phase, self.reason = 'PROBATION', None
        self.probe_successes = 0

    def success(self):
        if self.phase == 'PROBATION':
            self.probe_successes += 1
            if self.probe_successes >= self.required_successes:
                self.phase, self.reason = 'RUNNING', None
                self.recoveries += 1

    def primary_failed(self):
        if self.phase == 'PROBATION':
            self.phase, self.reason = 'LATCHED', 'primary_overrun_during_probation'
            return True
        return False

    def snapshot(self):
        return {'enabled': True, 'phase': self.phase, 'reason': self.reason,
                'cooldown_s': self.cooldown_s, 'window_s': self.window_s,
                'maximum_attempts': self.maximum_attempts,
                'required_successes': self.required_successes,
                'probe_successes': self.probe_successes, 'faults': self.faults,
                'attempts': self.attempts, 'recoveries': self.recoveries,
                'cooldown_until_monotonic_s': self.cooldown_until,
                'attempts_in_window': len(self.attempt_times)}
