"""Opt-in RAM-only crop preparation independent of synchronous Windows I/O.

The camera capture contract supplies an owned frame that consumers never mutate.
Only its reference is queued; one preparing frame and one latest pending frame.
No device, runner, identity storage, PNG encoding or network ownership here.
"""
import math
import threading
import time

from board.interaction.ui_contract import target_key


def producer_configuration(config):
    value = config.get('dpu_sface_producer')
    if value is None:
        return None
    if not isinstance(value, dict) or type(value.get('enabled')) is not bool:
        raise ValueError('Invalid SFace producer configuration')
    if not value['enabled']:
        if set(value) != {'enabled'}:
            raise ValueError('Disabled producer must contain only enabled=false')
        return None
    from board.identity.sface_shadow import shadow_configuration
    shadow = shadow_configuration(config)
    if (set(value) != {'enabled', 'interval_ms'} or type(value['interval_ms']) is not int
            or not 500 <= value['interval_ms'] <= 5000 or shadow is None
            or shadow['compare_cosine']):
        raise ValueError('Independent producer requires compute-only shadow and bounded preparation interval')
    return dict(value)


class SFaceProducer:
    def __init__(self, config, shadow, current_target, *, clock, guard_lock, align_crop, cv2):
        self.config = producer_configuration(config)
        if self.config is None or shadow is None or not callable(current_target) or guard_lock is None:
            raise ValueError('Producer requires explicit configuration and shared shadow/target guard')
        self.limits, self.shadow, self.current_target = config, shadow, current_target
        self.clock, self.guard_lock, self.align_crop, self.cv2 = clock, guard_lock, align_crop, cv2
        self.condition = threading.Condition()
        self.pending = None
        self.thread = None
        self.stopped = threading.Event()
        self.closed = False
        self.inflight = 0
        self.offered = self.enqueued = self.replaced = self.dropped = 0
        self.prepared = self.submitted = self.stale = self.failures = self.unready = 0
        self.last_error = ''
        self.generation = 0
        self.last_target = None

    def start(self):
        with self.condition:
            if self.thread is not None or self.closed:
                raise RuntimeError('Producer cannot start twice')
            self.thread = threading.Thread(target=self.work, name='sface-crop-prepare', daemon=True)
            self.thread.start()

    def offer_face(self, image, face, fid, stamp, key):
        """One caller: FaceTargetService's explicit fresh single-target callback.

        No array copy, alignment, quality calculation or waiting on this path.
        None face/key explicitly cancels a previously queued target.
        """
        self.offered += 1
        try:
            import numpy as np
            key = target_key(key) if key is not None else None
            if key != self.last_target or face is None:
                self.generation += 1
                self.last_target = key if face is not None else None
            generation = self.generation
            if not self.condition.acquire(blocking=False):
                self.dropped += 1
                return False
            try:
                if (self.closed or self.stopped.is_set() or key is None or face is None
                        or type(fid) is not int or fid < 1 or type(stamp) is not int
                        or not 0 <= self.clock()-stamp < self.shadow.config['max_source_age_ms']
                        or not isinstance(image, np.ndarray) or image.dtype != np.uint8
                        or image.shape != (480, 640, 3) or len(face) != 15
                        or not all(math.isfinite(float(v)) for v in face)
                        or min(face[2:4]) < self.limits['minimum_face_pixels']
                        or face[14] < self.limits['minimum_face_score']):
                    self.pending = None
                    self.dropped += 1
                    return False
                if not self.shadow.ready or self.shadow.closed or self.shadow.stopped.is_set():
                    self.unready += 1
                    return False
                self.replaced += int(self.pending is not None)
                self.pending = (image, tuple(face), fid, stamp, key, generation)
                self.enqueued += 1
                self.condition.notify()
                return True
            finally:
                self.condition.release()
        except Exception as exc:
            self.failures += 1
            self.last_error = type(exc).__name__[:64]
            return False

    def _valid(self, packet):
        return (not self.closed and packet[5] == self.generation
                and packet[4] == self.current_target()
                and 0 <= self.clock()-packet[3] < self.shadow.config['max_source_age_ms'])

    def _prepare(self, packet):
        with self.guard_lock:
            if not self._valid(packet):
                self.stale += 1
                return
        image, face, fid, stamp, key, _ = packet
        crop = self.align_crop(image, face)
        variance = float(self.cv2.Laplacian(self.cv2.cvtColor(crop, self.cv2.COLOR_BGR2GRAY),
                                          self.cv2.CV_64F).var())
        if not math.isfinite(variance) or variance < self.limits['minimum_blur_variance']:
            self.dropped += 1
            return
        from board.identity.sampling import pose_quality
        quality = pose_quality(face, variance)
        self.prepared += 1
        # Do not copy crop / acquire calibration ticket while holding state.lock.
        # Shadow's own before/after execution checks remain authoritative.
        with self.guard_lock:
            if not self._valid(packet):
                self.stale += 1
                return
        if self.shadow.offer(crop, fid, stamp, key, None, quality=quality):
            self.submitted += 1

    def work(self):
        try:
            next_at = 0.
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.closed or self.pending is not None)
                    if self.closed:
                        return
                    delay = next_at-time.monotonic()
                    if delay > 0:
                        self.condition.wait(delay)
                        continue
                    packet, self.pending = self.pending, None
                    self.inflight = 1
                try:
                    self._prepare(packet)
                except Exception as exc:
                    self.failures += 1
                    self.last_error = type(exc).__name__[:64]
                finally:
                    packet = None
                    with self.condition:
                        self.inflight = 0
                next_at = time.monotonic()+self.config['interval_ms']/1000.
        finally:
            with self.condition:
                self.pending = None
                self.inflight = 0
            self.stopped.set()

    def close(self, timeout=2):
        with self.condition:
            self.closed = True
            self.pending = None
            self.condition.notify_all()
        if self.thread is None:
            self.stopped.set()
        else:
            self.thread.join(timeout)
        return self.stopped.is_set()

    def health(self):
        with self.condition:
            return {'enabled': True, 'mode': 'INDEPENDENT_CROP_PREPARATION',
                    'ready': not self.closed and self.shadow.ready and not self.shadow.closed,
                    'closed': self.stopped.is_set(), 'stop_requested': self.closed,
                    'pending_frames': int(self.pending is not None), 'inflight_frames': self.inflight,
                    'interval_ms': self.config['interval_ms'],
                    'offered': self.offered, 'enqueued': self.enqueued, 'replaced': self.replaced,
                    'dropped': self.dropped, 'unready': self.unready, 'prepared': self.prepared,
                    'submitted': self.submitted, 'stale': self.stale, 'failures': self.failures,
                    'last_error': self.last_error}
