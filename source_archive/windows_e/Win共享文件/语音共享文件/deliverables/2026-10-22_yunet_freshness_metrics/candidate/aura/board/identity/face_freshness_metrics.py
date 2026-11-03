"""Opt-in bounded numeric observation; no frame, identity, runner or device data.

Mutation hooks leave the service's state lock first. A health caller may retain
an outer shared RLock; this recorder never acquires that application lock.
Snapshots use this recorder's lock, not transactions across the application.
Missing/invalid clocks are counted and omitted from duration summaries, never 0.
"""
from collections import deque
import math
import threading
import time


SCHEMA = 'aura-face-freshness-metrics-1'
MAX_INTEGER = (1 << 63) - 1
OUTCOME_CODES = {'error': 0, 'input_ttl': 1, 'slot_unavailable': 2,
                 'publish_ttl': 3, 'closed_after_detect': 4, 'published': 5}
EVENT_CODES = {'input_ttl': 1, 'slot_unavailable': 2, 'publish_ttl': 3,
               'closed_after_detect': 4, 'observed_freshness_gap': 5, 'clock_rejected': 6,
               'process_error': 7, 'post_commit_age_at_ttl': 8, 'closed': 9}
COUNTERS = (
    'offers', 'offers_accepted', 'offers_closed', 'latest_replaced',
    'attempts', 'attempts_finished', 'active_attempts', 'input_ttl_discarded',
    'slot_unavailable', 'publish_ttl_discarded', 'closed_after_detect_discarded',
    'published', 'published_positive', 'published_negative', 'published_multiface',
    'post_commit_observations', 'post_commit_observation_at_or_over_ttl', 'process_errors',
    'callback_errors', 'consecutive_slot_rejections', 'maximum_consecutive_slot_rejections',
    'clock_read_failures', 'invalid_clock_values', 'invalid_source_ages',
    'wall_pairs_rejected', 'cpu_pairs_rejected', 'source_clock_pairs_rejected',
    'observed_gap_intervals', 'definite_clipped_gap_intervals', 'counter_saturation',
    'numeric_summary_rejections', 'events_evicted',
)
SUMMARY_NAMES = (
    'attempt_wall_ms', 'attempt_thread_cpu_ms', 'detect_wall_ms', 'detect_thread_cpu_ms',
    'input_source_age_ms', 'pre_commit_check_source_age_ms', 'post_commit_source_age_ms',
    'post_commit_interval_ms', 'clipped_gap_lower_bound_ms', 'clipped_gap_upper_bound_ms',
)


def _integer(value):
    return type(value) is int and 0 <= value <= MAX_INTEGER


class FaceFreshnessMetrics:
    def __init__(self, *, ttl_ms, event_capacity=16, wall_clock=None, thread_clock=None,
                 source_alignment_tolerance_ms=50):
        if (not _integer(ttl_ms) or ttl_ms < 1 or type(event_capacity) is not int
                or not 1 <= event_capacity <= 64
                or type(source_alignment_tolerance_ms) is not int
                or not 0 <= source_alignment_tolerance_ms <= 1000):
            raise ValueError('Invalid freshness observation limits')
        self.ttl_ms = ttl_ms
        self.capacity = event_capacity
        self.wall_clock = wall_clock if wall_clock is not None else time.monotonic_ns
        self.thread_clock = thread_clock if thread_clock is not None else getattr(time, 'thread_time_ns', None)
        self.tolerance_ms = source_alignment_tolerance_ms
        self.lock = threading.Lock()
        self.counters = dict.fromkeys(COUNTERS, 0)
        self.summaries = {name: {'count': 0, 'total': 0., 'min': None, 'max': None, 'last': None}
                          for name in SUMMARY_NAMES}
        self.events = deque(maxlen=event_capacity)
        self.closed = False
        self.previous_publication = None
        self.first_attempt_mono_ns = None
        self.last_attempt_end_mono_ns = None
        self.last_publication_mono_ns = None

    def _inc(self, name, amount=1):
        old = self.counters[name]
        if old > MAX_INTEGER - amount:
            self.counters[name] = MAX_INTEGER
            if name != 'counter_saturation':
                self.counters['counter_saturation'] = min(MAX_INTEGER,
                    self.counters['counter_saturation'] + 1)
        else:
            self.counters[name] = old + amount

    def _summary(self, name, value):
        if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
            self._inc('numeric_summary_rejections')
            return
        row = self.summaries[name]
        total = row['total'] + value
        if not math.isfinite(total) or row['count'] == MAX_INTEGER:
            self._inc('numeric_summary_rejections')
            return
        row['count'] += 1
        row['total'] = total
        row['min'] = value if row['min'] is None else min(value, row['min'])
        row['max'] = value if row['max'] is None else max(value, row['max'])
        row['last'] = value

    def _event(self, code, mark=None, **numeric):
        if len(self.events) == self.capacity:
            self._inc('events_evicted')
        mark = mark if type(mark) is dict else {}
        row = {'event_code': EVENT_CODES[code], 'mono_ns': mark.get('mono_ns'),
               'thread_cpu_ns': mark.get('cpu_ns')}
        # All callers supply a fixed, internal key set. Invalid data stays null.
        row.update({name: value if type(value) in (int, float) and math.isfinite(value) else None
                    for name, value in numeric.items()})
        self.events.append(row)

    def mark(self):
        values = {}
        read_failures = invalid = 0
        for name, clock in (('mono_ns', self.wall_clock), ('cpu_ns', self.thread_clock)):
            try:
                value = clock() if callable(clock) else None
            except Exception:
                value = None
                read_failures += 1
            if not _integer(value):
                invalid += 1
                value = None
            values[name] = value
        values['thread_ident'] = threading.get_ident()
        with self.lock:
            self._inc('clock_read_failures', read_failures)
            self._inc('invalid_clock_values', invalid)
        return values

    def _duration(self, first, last, *, cpu=False):
        key = 'cpu_ns' if cpu else 'mono_ns'
        a = first.get(key) if type(first) is dict else None
        b = last.get(key) if type(last) is dict else None
        valid_thread = (not cpu or (type(first) is dict and type(last) is dict
                                    and first.get('thread_ident') == last.get('thread_ident')))
        if not _integer(a) or not _integer(b) or b < a or not valid_thread:
            self._inc('cpu_pairs_rejected' if cpu else 'wall_pairs_rejected')
            return None
        return (b - a) / 1e6

    def _source_age(self, now_ms, stamp_ms):
        if not _integer(now_ms) or not _integer(stamp_ms) or now_ms < stamp_ms:
            self._inc('invalid_source_ages')
            return None
        return now_ms - stamp_ms

    def offer(self, *, accepted, replaced):
        with self.lock:
            if self.closed:
                return
            self._inc('offers')
            self._inc('offers_accepted' if accepted else 'offers_closed')
            if accepted and replaced:
                self._inc('latest_replaced')

    def begin(self, stamp_ms):
        start = self.mark()
        with self.lock:
            if self.closed:
                return None
            self._inc('attempts')
            self._inc('active_attempts')
            if self.first_attempt_mono_ns is None:
                self.first_attempt_mono_ns = start['mono_ns']
        return {'start': start, 'stamp_ms': stamp_ms, 'input_now_ms': None,
                'outcome_code': OUTCOME_CODES['error'], 'detect_start': None,
                'detect_end': None, 'callback_started': False, 'callback_completed': False,
                'finished': False, 'publication_observed': False, 'pre_commit_check_now_ms': None}

    def publish(self, token, source_now_ms, face_count):
        mark = self.mark()
        if type(token) is not dict or type(face_count) is not int or not 0 <= face_count <= 16:
            raise ValueError('Invalid numeric publication observation')
        with self.lock:
            if self.closed or token.get('publication_observed'):
                return
            token['publication_observed'] = True
            self._inc('post_commit_observations')
            self._inc('published_positive' if face_count else 'published_negative')
            if face_count > 1:
                self._inc('published_multiface')
            stamp = token.get('stamp_ms')
            age = self._source_age(source_now_ms, stamp)
            if age is not None:
                self._summary('post_commit_source_age_ms', age)
                if age >= self.ttl_ms:
                    self._inc('post_commit_observation_at_or_over_ttl')
                    self._event('post_commit_age_at_ttl', mark, age_ms=age)
            checked_now = token.get('pre_commit_check_now_ms')
            check_age = self._source_age(checked_now, stamp)
            if check_age is not None:
                self._summary('pre_commit_check_source_age_ms', check_age)
            mono = mark['mono_ns']
            previous = self.previous_publication
            if previous is not None:
                interval = self._duration(previous['mark'], mark)
                if interval is not None:
                    self._summary('post_commit_interval_ms', interval)
                aligned = (interval is not None and age is not None
                           and _integer(previous['source_now_ms'])
                           and _integer(previous['stamp_ms'])
                           and source_now_ms >= previous['source_now_ms']
                           and stamp >= previous['stamp_ms']
                           and _integer(checked_now)
                           and previous['source_now_ms'] <= checked_now <= source_now_ms
                           and abs((source_now_ms-previous['source_now_ms'])-interval) <= self.tolerance_ms)
                if aligned:
                    # The previous source stamp, NOT previous publish time,
                    # determines expiry. Clip a previously expired publication.
                    expiry = previous['stamp_ms'] + self.ttl_ms
                    anchor = max(expiry, previous['source_now_ms'])
                    lower = max(0, checked_now - anchor)
                    upper = max(0, source_now_ms - anchor)
                    self._summary('clipped_gap_lower_bound_ms', lower)
                    self._summary('clipped_gap_upper_bound_ms', upper)
                    if lower > 0:
                        self._inc('definite_clipped_gap_intervals')
                    if upper > 0:
                        self._inc('observed_gap_intervals')
                        self._event('observed_freshness_gap', mark,
                                    lower_bound_ms=lower, upper_bound_ms=upper,
                                    previous_stamp_ms=previous['stamp_ms'], previous_expiry_ms=expiry,
                                    pre_commit_check_now_ms=checked_now, source_now_ms=source_now_ms)
                else:
                    self._inc('source_clock_pairs_rejected')
                    self._event('clock_rejected', mark)
            self.previous_publication = ({'mark': dict(mark), 'source_now_ms': source_now_ms,
                                          'stamp_ms': stamp} if age is not None and _integer(mono) else None)
            self.last_publication_mono_ns = mono

    def finish(self, token):
        if type(token) is not dict:
            return
        end = self.mark()
        with self.lock:
            if self.closed or token.get('finished'):
                return
            token['finished'] = True
            self._inc('attempts_finished')
            self.counters['active_attempts'] = max(0, self.counters['active_attempts'] - 1)
            self.last_attempt_end_mono_ns = end['mono_ns']
            for name, cpu in (('attempt_wall_ms', False), ('attempt_thread_cpu_ms', True)):
                value = self._duration(token.get('start'), end, cpu=cpu)
                if value is not None:
                    self._summary(name, value)
            if token.get('detect_start') is not None and token.get('detect_end') is not None:
                for name, cpu in (('detect_wall_ms', False), ('detect_thread_cpu_ms', True)):
                    value = self._duration(token['detect_start'], token['detect_end'], cpu=cpu)
                    if value is not None:
                        self._summary(name, value)
            age = self._source_age(token.get('input_now_ms'), token.get('stamp_ms'))
            if age is not None:
                self._summary('input_source_age_ms', age)
            code = token.get('outcome_code')
            outcomes = {
                OUTCOME_CODES['input_ttl']: ('input_ttl_discarded', 'input_ttl'),
                OUTCOME_CODES['slot_unavailable']: ('slot_unavailable', 'slot_unavailable'),
                OUTCOME_CODES['publish_ttl']: ('publish_ttl_discarded', 'publish_ttl'),
                OUTCOME_CODES['closed_after_detect']: ('closed_after_detect_discarded', 'closed_after_detect'),
                OUTCOME_CODES['published']: ('published', None),
            }
            if code in outcomes:
                counter, event = outcomes[code]
                self._inc(counter)
                if event is not None:
                    self._event(event, end, source_age_ms=age)
            else:
                self._inc('process_errors')
                self._event('process_error', end)
            if token.get('callback_started') and not token.get('callback_completed'):
                self._inc('callback_errors')
            if code == OUTCOME_CODES['slot_unavailable']:
                self._inc('consecutive_slot_rejections')
                self.counters['maximum_consecutive_slot_rejections'] = max(
                    self.counters['maximum_consecutive_slot_rejections'],
                    self.counters['consecutive_slot_rejections'])
            else:
                self.counters['consecutive_slot_rejections'] = 0

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self._event('closed')

    def snapshot(self):
        with self.lock:
            summaries = {name: {'count': row['count'], 'total_ms': row['total'],
                               'min_ms': row['min'], 'max_ms': row['max'], 'last_ms': row['last'],
                               'mean_ms': row['total']/row['count'] if row['count'] else None}
                         for name, row in self.summaries.items()}
            return {
                'schema_version': SCHEMA, 'enabled': True, 'collecting': not self.closed,
                'closed': self.closed, 'ttl_ms': self.ttl_ms,
                'scope': 'All observed attempts/publications since explicit enable; no sensor exposure or identity accuracy claim',
                'source_clock': 'service millis/appsink dequeue timestamp',
                'duration_clock': 'monotonic_ns; thread CPU only for the calling thread',
                'snapshot_scope': 'recorder lock only; not an atomic camera/service/recorder transaction',
                'publication_measurement_point': 'post-state-lock release observation; scheduler delay before clocks is unknown; not exact commit time',
                'post_commit_ttl_scope': 'age at observation >= TTL does not mean the original pre-commit TTL gate accepted stale input',
                'gap_scope': 'bounds from existing pre-commit TTL check and post-commit observation; clipped to previous observation; no window-head/tail extrapolation',
                'streak_scope': 'consecutive finished SlotUnavailable attempts; any other outcome resets',
                'source_alignment_tolerance_ms': self.tolerance_ms,
                'clock_rejection_scope': 'backward/missing/order/alignment rejection; not proof of a physical clock jump',
                'missing_clock_value': None, 'event_capacity': self.capacity,
                'event_codes': dict(EVENT_CODES), 'counters': dict(self.counters),
                'summaries': summaries, 'events': [dict(row) for row in self.events],
                'first_attempt_mono_ns': self.first_attempt_mono_ns,
                'last_attempt_end_mono_ns': self.last_attempt_end_mono_ns,
                'last_publication_mono_ns': self.last_publication_mono_ns,
            }
