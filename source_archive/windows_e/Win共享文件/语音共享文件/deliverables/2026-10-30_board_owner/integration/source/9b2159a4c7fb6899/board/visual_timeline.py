"""Stable person-count events from the existing camera owner's health samples.

Call from a board worker, never a GTK tick. No capture, image upload, identity
lookup, or network operation occurs here. Source frame progress, not UI refresh
progress, establishes stability. Camera failure never means a person left.
"""
import hashlib
import json
import math
import time


class VisualTimelineCollector:
    def __init__(self, board_boot_id, sink, scope, *, stable_ms=600,
                 min_frames=3, min_event_interval_ms=1000, max_age_ms=750,
                 clock_ms=None, utc_clock=time.time, allow_fixture=False):
        if not isinstance(board_boot_id, str) or not 1 <= len(board_boot_id) <= 96:
            raise ValueError('Invalid board boot')
        if (type(stable_ms) is not int or not 0 <= stable_ms <= 10000
                or type(min_frames) is not int or not 2 <= min_frames <= 100
                or type(max_age_ms) is not int or not 1 <= max_age_ms <= 750
                or type(min_event_interval_ms) is not int or min_event_interval_ms < 0):
            raise ValueError('Invalid observation bounds')
        self.boot, self.sink, self.scope = board_boot_id, sink, dict(scope)
        self.stable_ms, self.min_frames = stable_ms, min_frames
        self.min_interval, self.max_age = min_event_interval_ms, max_age_ms
        self.clock_ms = clock_ms or (lambda: int(time.monotonic() * 1000))
        self.utc_clock, self.allow_fixture = utc_clock, allow_fixture
        self.source = None
        self.retired_sources = set()
        self.last_frame, self.last_request = -1, -1
        self.candidate = self.committed_count = self.pending = None
        self.last_event_ms = None
        self.accepted = self.emitted = self.rejected = 0
        self.last_reason = ''

    def _reject(self, reason, *, invalidate=False):
        self.rejected += 1
        self.last_reason = reason
        if invalidate:
            self.candidate = self.pending = self.committed_count = None
        return None

    @staticmethod
    def _number(value):
        return type(value) in (int, float) and math.isfinite(value)

    def ingest_health(self, health, *, requested_mono_ms, received_mono_ms=None,
                      source_kind='actual'):
        """Use board-local /health; pass the request start and receive clocks.

        Subtracting the reported source age from the request start provides a
        conservative source-time bound. Incoming JSON is never copied wholesale.
        """
        now = self.clock_ms() if received_mono_ms is None else received_mono_ms
        if (not self._number(now) or not self._number(requested_mono_ms)
                or requested_mono_ms > now):
            return self._reject('invalid_clock', invalidate=True)
        if requested_mono_ms < self.last_request:
            return self._reject('out_of_order_response')
        self.last_request = requested_mono_ms
        if source_kind != 'actual' and not (self.allow_fixture and source_kind == 'fixture'):
            return self._reject('non_actual_source', invalidate=True)
        if not isinstance(health, dict) or health.get('board_boot_id') != self.boot:
            return self._reject('boot_mismatch', invalidate=True)
        source = tuple(health.get(name) for name in ('service_epoch', 'camera_epoch'))
        if any(not isinstance(value, str) or not 1 <= len(value) <= 96 for value in source):
            return self._reject('missing_source', invalidate=True)
        if source in self.retired_sources:
            return self._reject('retired_source')
        if (health.get('camera_error') or health.get('detector_error')
                or health.get('role') != 'DPU_YOLOX_PERSON_PREVIEW'
                or health.get('detector', {}).get('count_kind') != 'people'
                or health.get('timestamp_kind') != 'appsink_dequeue_monotonic'):
            return self._reject('source_unavailable_or_not_person_detector', invalidate=True)
        age, capture_age = health.get('observation_age_ms'), health.get('capture_age_ms')
        if (not self._number(age) or not self._number(capture_age)
                or age < 0 or capture_age < 0
                or now - requested_mono_ms + max(age, capture_age) >= self.max_age):
            return self._reject('stale_source', invalidate=True)
        frame, count = health.get('observation_frame_id'), health.get('people_count')
        if (type(frame) is not int or frame < 1 or type(count) is not int
                or not 0 <= count <= 1000):
            return self._reject('invalid_observation', invalidate=True)
        if source != self.source:
            if len(self.retired_sources) >= 16:
                return self._reject('source_change_limit', invalidate=True)
            if self.source is not None:
                self.retired_sources.add(self.source)
            self.source, self.last_frame = source, -1
            self.candidate = self.pending = self.committed_count = None
        if frame <= self.last_frame:
            return self._reject('duplicate_or_old_source_frame')
        self.last_frame = frame
        source_ms = requested_mono_ms - age
        self.accepted += 1
        self.last_reason = ''
        if self.candidate is None or self.candidate['count'] != count:
            self.candidate = dict(count=count, first_frame=frame, first_ms=source_ms, frames=1)
            self.pending = None
        else:
            self.candidate['frames'] += 1
        if (count == self.committed_count or self.candidate['frames'] < self.min_frames
                or source_ms - self.candidate['first_ms'] < self.stable_ms
                or self.last_event_ms is not None and now - self.last_event_ms < self.min_interval):
            return None
        if self.pending is None:
            event_kind = 'person_count_observed' if count else 'no_person_detected'
            identity = (self.boot, source, self.candidate['first_frame'], count, source_kind)
            event_id = hashlib.sha256(json.dumps(identity, separators=(',', ':')).encode()).hexdigest()
            text = ('摄像头视野内稳定检测到%d个人体目标。' % count if count
                    else '摄像头视野内当前未检测到人体目标。')
            self.pending = dict(event_id=event_id, text=text, metadata=dict(
                evidence='visual_observation', numbers=[count], speaker_known=False,
                source_id=hashlib.sha256(json.dumps((self.boot, source, frame)).encode()).hexdigest(),
                time_basis='board_camera_health_source_bound',
                occurred_utc=self.utc_clock() - (now - source_ms) / 1000,
                claims=[{'field': 'event_kind', 'value': event_kind},
                        {'field': 'people_count', 'value': count},
                        {'field': 'source_frame_id', 'value': frame},
                        {'field': 'source_kind', 'value': source_kind}]))
        event = self.pending
        # Freeze the event across an uncertain write result. The store must use
        # event_id idempotently; a new source frame must not create a duplicate.
        self.sink(self.scope, event['event_id'], 'camera_observed', event['text'],
                  topic='视觉', metadata=event['metadata'])
        self.committed_count = count
        self.last_event_ms = now
        self.pending = None
        self.emitted += 1
        return dict(event)

    def health(self):
        return dict(accepted_frames=self.accepted, emitted_events=self.emitted,
                    rejected_samples=self.rejected, last_reason=self.last_reason,
                    capture_owner='existing_camera_service', raw_images_stored=False,
                    identity_access_granted=False, current_count=self.committed_count)
