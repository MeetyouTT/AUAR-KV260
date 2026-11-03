"""Bounded idle-memory retry scheduling; no Store/schema/retention changes.

The original worker owns leases, foreground cancellation and atomic publication.
This wrapper only delays repeated failed attempts, using a monotonic RAM timer.
It never exports exception messages or source identifiers.
"""
import sqlite3
import time

from common.board_memory import BoardMemoryWorker, MemoryBusy
from common.board_timeline_clock import ClockUnavailable


class BoardMemoryBackoffWorker(BoardMemoryWorker):
    """Retry real failures after 3, 6, 12, 24, 48, then at most 60 seconds.

    Successful commits clear the streak. Idle/no-work, cancellation, unsafe
    clock and stale-source/lease results do not add failures or extend cooldown.
    A fresh worker starts with no cooldown; no body is discarded by this layer.
    """
    def __init__(self, store, summarize, *, retry_clock=time.monotonic, **kwargs):
        if not callable(retry_clock):
            raise TypeError('Supply a monotonic retry clock')
        self._retry_clock = retry_clock
        self._retry_state = (0, 0., 0., '')
        self._summary_failure = ''
        self._step_failed = False
        self._retry_skipped = False
        self._summary_metadata = getattr(summarize, 'failure_metadata', None)

        def classified_summary(prepared, cancelled):
            try:
                return summarize(prepared, cancelled)
            except Exception as exc:
                if isinstance(exc, InterruptedError):
                    self._summary_failure = 'cancelled'
                elif isinstance(exc, TimeoutError):
                    self._summary_failure = 'deadline_exceeded'
                # Transport cancellation can surface as a closed socket instead
                # of InterruptedError. The original predicate covers foreground
                # admission and invalidated source revisions/leases.
                try:
                    if cancelled():
                        self._summary_failure = 'cancelled'
                except (ClockUnavailable, MemoryBusy, sqlite3.Error):
                    pass
                raise

        super().__init__(store, classified_summary, **kwargs)

    def _record_failure(self, reason):
        streak = self._retry_state[0] + 1
        delay = min(60., 3. * (2 ** min(streak - 1, 5)))
        self._retry_state = (streak, self._retry_clock() + delay, delay, reason)
        self._step_failed = True

    def _fail_task(self, task_id, token, reason):
        # Preserve original release/diagnostics and its fixed reason allowlist.
        # Correct the original broad model_failed mapping by exception type or
        # an observed original cancellation predicate, never by parsing text.
        if self._summary_failure == 'cancelled' and reason != 'clock_unverified':
            reason = 'cancelled'
        elif reason == 'model_failed' and self._summary_failure == 'deadline_exceeded':
            reason = 'deadline_exceeded'
        if reason in ('candidate_rejected', 'model_failed', 'deadline_exceeded',
                      'database_busy', 'compaction_failed'):
            self._record_failure(reason)
        return super()._fail_task(task_id, token, reason)

    def step(self):
        self._retry_skipped = False
        if self.stop.is_set():
            return False
        if self._retry_clock() < self._retry_state[1]:
            self._retry_skipped = True
            return False
        self._summary_failure = ''
        self._step_failed = False
        try:
            committed = super().step()
        except (MemoryBusy, sqlite3.Error):
            # Keep the original run-loop exception handling visible. A failure
            # before a task is leased must not bypass retry bounds either.
            if not self._step_failed:
                self._record_failure('database_busy')
            raise
        if committed:
            self._retry_state = (0, 0., 0., '')
        return committed

    def health(self):
        value = super().health()
        streak, due, delay, reason = self._retry_state
        value['retry_backoff'] = dict(failure_streak=streak,
            retry_in_seconds=max(0., due - self._retry_clock()),
            last_delay_seconds=delay, last_failure_code=reason,
            skipped_for_cooldown=self._retry_skipped, maximum_seconds=60.)
        if callable(self._summary_metadata):
            value['summary_diagnostics'] = self._summary_metadata()
        return value
