"""Bounded idle-memory retry scheduling; no schema/retention changes.

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
    Rejected source batches have a separate 600-second RAM cooldown, capped at
    64 batches. An unrelated commit does not clear their cooldowns.
    A fresh worker starts with no cooldown; no body is discarded by this layer.
    """
    def __init__(self, store, summarize, *, retry_clock=time.monotonic, **kwargs):
        if not callable(retry_clock):
            raise TypeError('Supply a monotonic retry clock')
        self._retry_clock = retry_clock
        self._retry_state = (0, 0., 0., '')
        self._source_cooldowns = ()
        self._source_versions = ()
        self._summary_failure = ''
        self._step_failed = False
        self._retry_skipped = False
        self._summary_metadata = getattr(summarize, 'failure_metadata', None)

        def classified_summary(prepared, cancelled):
            self._source_versions = tuple(sorted((source['event_id'], source['revision'])
                for source in prepared['sources']))
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

    def _prepare_compaction(self):
        now = self._retry_clock()
        self._source_cooldowns = tuple((versions, due) for versions, due in self._source_cooldowns if due > now)
        if not self._source_cooldowns:
            return super()._prepare_compaction()
        return self.store.prepare_compaction(worker_id=self.worker_id, max_events=self.max_events,
            lease_seconds=self.lease_seconds,
            excluded_source_versions=tuple(versions for versions, _ in self._source_cooldowns))

    def _record_source_failure(self):
        now = self._retry_clock()
        versions = self._source_versions
        retained = tuple((batch, due) for batch, due in self._source_cooldowns
                         if due > now and batch != versions)
        self._source_cooldowns = retained[-63:] + ((versions, now + 600.),)

    def _fail_task(self, task_id, token, reason):
        # Preserve original release/diagnostics and its fixed reason allowlist.
        # Correct the original broad model_failed mapping by exception type or
        # an observed original cancellation predicate, never by parsing text.
        if self._summary_failure == 'cancelled' and reason != 'clock_unverified':
            reason = 'cancelled'
        elif reason == 'model_failed' and self._summary_failure == 'deadline_exceeded':
            reason = 'deadline_exceeded'
        if reason == 'candidate_rejected' and self._source_versions:
            try:
                with self.compaction_guard_factory():
                    current = not self.stop.is_set() and self.idle() and self.store.compaction_current(task_id, token)
                    if current:
                        result = super()._fail_task(task_id, token, reason)
                if current:
                    if self._failure_released and self.error == reason and not self.stop.is_set() and self.idle():
                        self._record_source_failure()
                    return result
                reason = 'cancelled'
            except ClockUnavailable:
                reason = 'clock_unverified'
            except (MemoryBusy, sqlite3.Error):
                reason = 'database_busy'
        result = super()._fail_task(task_id, token, reason)
        if self._failure_released and self.error == reason and reason in (
                'model_failed', 'deadline_exceeded', 'database_busy', 'compaction_failed'):
            self._record_failure(reason)
        return result

    def step(self):
        self._retry_skipped = False
        if self.stop.is_set():
            return False
        if self._retry_clock() < self._retry_state[1]:
            self._retry_skipped = True
            return False
        self._summary_failure = ''
        self._source_versions = ()
        self._step_failed = False
        try:
            committed = super().step()
        except (MemoryBusy, sqlite3.Error):
            # Keep the original run-loop exception handling visible. A failure
            # before a task is leased must not bypass retry bounds either.
            if not self._step_failed:
                self._record_failure('database_busy')
            raise
        finally:
            self._source_versions = ()
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
        now = self._retry_clock()
        pending = [due for _, due in self._source_cooldowns if due > now]
        value['source_cooldown'] = dict(cached_batches=len(pending),
            retry_in_seconds=max(0., min(pending) - now) if pending else 0.,
            delay_seconds=600., capacity_batches=64)
        if callable(self._summary_metadata):
            value['summary_diagnostics'] = self._summary_metadata()
        return value
