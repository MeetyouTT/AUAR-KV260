"""Bounded optional DPU shadow; Windows alone supplies identity decisions.

One immutable crop/reference in flight and one latest pending item, RAM only.
No database, identity result, enrollment, camera, service, or device ownership.
"""
from contextlib import contextmanager
import math
from pathlib import Path
import threading
import time

from board.identity.deferred import DeferredIdentity
from board.identity.model_store import MODEL_ID, MODEL_SHA256, WINDOWS_MODEL_ID
from board.interaction.ui_contract import millis, target_key


def shadow_configuration(config):
    """Pure validation, default off; never opens artifacts, devices or stores."""
    value = config.get('dpu_sface_shadow')
    if value is None:
        return None
    if not isinstance(value, dict) or type(value.get('enabled')) is not bool:
        raise ValueError('Invalid DPU SFace shadow configuration')
    if not value['enabled']:
        if set(value) != {'enabled'}:
            raise ValueError('Disabled shadow configuration must contain only enabled=false')
        return None
    required = {'enabled','model','manifest','model_sha256','manifest_sha256',
                'max_source_age_ms','interval_ms','compare_cosine'}
    primary = config.get('feature_backend') or {}
    if (set(value) != required or primary.get('kind') != 'windows_sface'
            or config.get('model_id') != WINDOWS_MODEL_ID):
        raise ValueError('SFace shadow requires the original Windows FP32 identity backend')
    if (value['model_sha256'] != MODEL_SHA256 or type(value['interval_ms']) is not int
            or not 500 <= value['interval_ms'] <= 5000 or type(value['max_source_age_ms']) is not int
            or not 100 <= value['max_source_age_ms'] <= min(1500,config['result_ttl_ms'])
            or type(value['compare_cosine']) is not bool):
        raise ValueError('Invalid SFace shadow model, source lifetime or rate')
    for key in ('model','manifest'):
        if not isinstance(value[key], str) or not Path(value[key]).is_absolute():
            raise ValueError('Shadow model/manifest require explicit absolute paths')
    digest = value['manifest_sha256']
    if not isinstance(digest,str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Shadow requires an explicit compiler manifest SHA256')
    return dict(value)


@contextmanager
def unlocked():
    yield


class SFaceShadow:
    def __init__(self, config, schedule, owner, current_target, *, clock=millis,
                 guard_lock=None, embedder_factory=None):
        self.config = shadow_configuration(config)
        if self.config is None:
            raise ValueError('Explicit enabled shadow configuration is required')
        if schedule is None or owner is None or not callable(current_target) or not callable(clock):
            raise ValueError('Shadow requires the existing camera owner, scheduler and target check')
        self.schedule, self.owner, self.current_target = schedule, owner, current_target
        self.clock, self.guard_lock = clock, guard_lock
        self.factory = embedder_factory or self._make_embedder
        self.condition = threading.Condition()
        self.thread = None
        self.stopped = threading.Event()
        self.pending = None
        self.inflight = 0
        self.closed = self.ready = False
        self.embedder = None
        self.offered = self.enqueued = self.replaced = self.producer_dropped = 0
        self.processed = self.accepted = self.stale = self.deferred = self.failures = 0
        self.last_error = ''
        self.latency_sum = self.latency_min = self.latency_max = 0.
        self.cosine_count = 0
        self.cosine_sum = self.cosine_min = self.cosine_max = 0.

    def _make_embedder(self):
        from board.vision.dpu_sface import DpuSFace
        value = self.config
        feature = {k:value[k] for k in ('model','manifest','model_sha256','manifest_sha256','max_source_age_ms')}
        feature['kind'] = 'dpu_sface'
        # DpuSFace only needs its pinned tensor contract. No store/config
        # factory is called and no INT8 database/threshold is required.
        return DpuSFace({'model_id':MODEL_ID, 'feature_backend':feature},
                        self.schedule, self.owner, self.clock)

    def _guard(self):
        return self.guard_lock if self.guard_lock is not None else unlocked()

    def _valid(self, packet):
        return (not self.closed and packet['target'] == self.current_target()
                and 0 <= self.clock()-packet['stamp'] < self.config['max_source_age_ms'])

    def start(self):
        with self.condition:
            if self.thread is not None or self.closed:
                raise RuntimeError('Shadow cannot start twice')
            self.thread = threading.Thread(target=self.work, name='sface-dpu-shadow', daemon=True)
            self.thread.start()

    def offer(self, crop, fid, stamp, key, reference):
        """Never waits for shadow state or inference; primary keeps its vector."""
        self.offered += 1  # The extractor is the sole producer.
        try:
            import numpy as np
            if (self.closed or self.stopped.is_set() or type(fid) is not int or fid < 1
                    or type(stamp) is not int or not 0 <= self.clock()-stamp < self.config['max_source_age_ms']
                    or not isinstance(crop,np.ndarray) or crop.dtype != np.uint8 or crop.shape != (112,112,3)):
                self.producer_dropped += 1
                return False
            target = target_key(key)
            original = None
            if self.config['compare_cosine']:
                values = tuple(float(v) for v in reference)
                norm = math.sqrt(sum(v*v for v in values))
                if len(values) != 128 or not all(math.isfinite(v) for v in values) or norm <= 1e-12:
                    self.producer_dropped += 1
                    return False
                original = tuple(v/norm for v in values)
            # One bounded 37,632-byte private copy; producer/camera buffers can
            # be released or reused immediately after this nonblocking offer.
            image = np.array(crop, dtype=np.uint8, order='C', copy=True)
            image.flags.writeable = False
            packet = {'crop':image,'fid':fid,'stamp':stamp,'target':target,'reference':original}
            if not self.condition.acquire(blocking=False):
                self.producer_dropped += 1
                return False
            try:
                if self.closed or self.stopped.is_set():
                    self.producer_dropped += 1
                    return False
                self.replaced += int(self.pending is not None)
                self.pending = packet
                self.enqueued += 1
                self.condition.notify()
                return True
            finally:
                self.condition.release()
        except Exception:
            # Shadow input/copy/validation failure cannot escape into primary.
            self.producer_dropped += 1
            return False

    @staticmethod
    def _cosine(feature, reference):
        values = tuple(float(v) for v in feature)
        norm = math.sqrt(sum(v*v for v in values))
        if len(values) != 128 or not all(math.isfinite(v) for v in values) or norm <= 1e-12:
            raise ValueError('Invalid shadow embedding')
        return max(-1., min(1., sum(a*b for a,b in zip(values,reference))/norm))

    def _process(self, packet):
        with self._guard():
            valid = self._valid(packet)
        if not valid:
            with self.condition:self.stale += 1
            return
        started = time.monotonic()
        try:
            feature = self.embedder.feature(packet['crop'], source_mono_ms=packet['stamp'])
            cosine = self._cosine(feature,packet['reference']) if self.config['compare_cosine'] else None
            elapsed = (time.monotonic()-started)*1000
            # Publication lock order matches the parent health path: camera
            # state lock then shadow condition. Never hold either during DPU.
            with self._guard():
                valid = self._valid(packet)
                with self.condition:
                    self.processed += 1
                    if not valid:
                        self.stale += 1
                        return
                    self.accepted += 1
                    self.latency_sum += elapsed
                    self.latency_min = elapsed if self.accepted == 1 else min(self.latency_min,elapsed)
                    self.latency_max = max(self.latency_max,elapsed)
                    if cosine is not None:
                        self.cosine_count += 1
                        self.cosine_sum += cosine
                        self.cosine_min = cosine if self.cosine_count == 1 else min(self.cosine_min,cosine)
                        self.cosine_max = cosine if self.cosine_count == 1 else max(self.cosine_max,cosine)
        except DeferredIdentity:
            with self.condition:self.deferred += 1
        except Exception as exc:
            with self.condition:
                self.failures += 1
                self.last_error = type(exc).__name__[:64]

    def work(self):
        try:
            embedder = self.factory()
            with self.condition:
                self.embedder, self.ready = embedder, True
            next_at = 0.
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.closed or self.pending is not None)
                    if self.closed:return
                    delay = next_at-time.monotonic()
                    if delay > 0:
                        self.condition.wait(delay)
                        continue
                    packet, self.pending = self.pending, None
                    self.inflight = 1
                self._process(packet)
                # Drop all per-source biometric references before waiting.
                packet = None
                with self.condition:self.inflight = 0
                next_at = time.monotonic()+self.config['interval_ms']/1000.
        except Exception as exc:
            with self.condition:
                self.failures += 1
                self.last_error = type(exc).__name__[:64]
        finally:
            if self.embedder is not None:
                try:self.embedder.close()
                except Exception as exc:
                    with self.condition:
                        self.failures += 1
                        self.last_error = type(exc).__name__[:64]
            with self.condition:
                self.ready = False
                self.pending = None
                self.inflight = 0
            self.stopped.set()

    def health(self):
        with self.condition:
            try:
                runtime = self.embedder.health() if self.embedder is not None and callable(getattr(self.embedder,'health',None)) else None
            except Exception as exc:
                runtime = {'error':type(exc).__name__[:64]}
            return {'enabled':True,'mode':'SHADOW_ONLY_WINDOWS_IDENTITY','model_id':MODEL_ID,
                'ready':self.ready,'closed':self.stopped.is_set(),'stop_requested':self.closed,'stopped':self.stopped.is_set(),
                'pending_frames':int(self.pending is not None),'inflight_frames':self.inflight,
                'offered':self.offered,'enqueued':self.enqueued,'replaced':self.replaced,
                'producer_dropped':self.producer_dropped,'processed':self.processed,'accepted':self.accepted,
                'stale':self.stale,'deferred':self.deferred,'failures':self.failures,'last_error':self.last_error,
                'accepted_latency_ms':{'count':self.accepted,'mean':self.latency_sum/self.accepted if self.accepted else None,
                    'min':self.latency_min if self.accepted else None,'max':self.latency_max if self.accepted else None},
                'same_crop_cosine':{'count':self.cosine_count,'mean':self.cosine_sum/self.cosine_count if self.cosine_count else None,
                    'min':self.cosine_min if self.cosine_count else None,'max':self.cosine_max if self.cosine_count else None},
                'execution':runtime,'identity_decisions_from_shadow':0,'templates_written':0}

    def close(self, timeout=5):
        with self.condition:
            self.closed = True
            self.pending = None
            self.condition.notify_all()
        if self.thread is None:
            self.stopped.set()
            return True
        self.thread.join(timeout)
        # The worker owns its runner and closes it after the in-flight job.
        # Do not close an executing runner or the shared owner from this thread.
        return self.stopped.is_set()
