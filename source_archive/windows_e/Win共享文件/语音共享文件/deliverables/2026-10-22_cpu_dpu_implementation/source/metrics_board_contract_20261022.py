"""Bounded numeric stage timings. No frames, vectors, names or track IDs.

All durations use monotonic_ns; source ages retain the existing appsink-dequeue
millisecond semantics. Quantiles describe the recent bounded window only.
"""
from collections import deque
import math
import threading
import time


STAGES = frozenset({
    'capture.callback_prepare', 'yolo.schedule_wait', 'yolo.native_and_decode',
    'yolo.track', 'yolo.path', 'yolo.source_age_at_start', 'yolo.publish_source_age',
    'preview.render_encode_publish', 'preview.publish_source_age',
    'yunet.allocate', 'yunet.slot_wait', 'yunet.execute_wait', 'yunet.dequantize',
    'sface.allocate', 'sface.slot_wait', 'sface.execute_wait', 'sface.dequantize',
    'sface.normalize_input', 'sface.validate_output',
})


class PipelineMetrics:
    def __init__(self, *, enabled=False, capacity=256):
        if type(enabled) is not bool or type(capacity) is not int or not 16 <= capacity <= 1024:
            raise ValueError('Invalid bounded pipeline metrics configuration')
        self.enabled, self.capacity = enabled, capacity
        self.lock = threading.Lock()
        self.stages = {}

    def value(self, stage, milliseconds):
        if not self.enabled:
            return
        if stage not in STAGES or type(milliseconds) not in (float, int) or not math.isfinite(milliseconds) or milliseconds < 0:
            raise ValueError('Invalid numeric pipeline timing')
        with self.lock:
            row = self.stages.setdefault(stage, {'count':0, 'sum':0., 'minimum':None,
                'maximum':None, 'recent':deque(maxlen=self.capacity)})
            row['count'] += 1
            row['sum'] += milliseconds
            row['minimum'] = milliseconds if row['minimum'] is None else min(row['minimum'], milliseconds)
            row['maximum'] = milliseconds if row['maximum'] is None else max(row['maximum'], milliseconds)
            row['recent'].append(float(milliseconds))

    def elapsed(self, stage, started_ns):
        if self.enabled:
            self.value(stage, (time.monotonic_ns()-started_ns)/1e6)

    def snapshot(self):
        if not self.enabled:
            return {'enabled':False}
        with self.lock:
            copied={key:{**{k:v for k,v in value.items() if k!='recent'},
                'recent':tuple(value['recent'])} for key,value in self.stages.items()}
        rows={}
        for key,value in copied.items():
            recent=sorted(value['recent']);n=len(recent)
            rows[key]={'count':value['count'], 'total_ms':value['sum'],
                'mean_ms':value['sum']/value['count'], 'min_ms':value['minimum'],
                'max_ms':value['maximum'], 'recent_count':n,
                'recent_p50_ms':recent[math.ceil(.5*n)-1],
                'recent_p95_ms':recent[math.ceil(.95*n)-1]}
        return {'enabled':True,'schema_version':'aura-pipeline-metrics-1',
            'clock':'monotonic_ns', 'unit':'milliseconds', 'capacity_per_stage':self.capacity,
            'quantile_scope':'most recent bounded samples per stage; not all calls or health-snapshot quantiles',
            'source_age_scope':'existing appsink-dequeue timestamp; not sensor exposure or glass-to-glass',
            'yolo_native_scope':'native preprocessing + DPU + native decode; not DPU-only time',
            'stages':rows}

m=PipelineMetrics(enabled=True,capacity=16)
for n in range(100):m.value("yolo.path",n)
r=m.snapshot()["stages"]["yolo.path"]
assert r["count"]==100 and r["recent_count"]==16 and r["recent_p50_ms"]==91 and r["mean_ms"]==49.5
assert PipelineMetrics().snapshot()=={"enabled":False}
import json
print(json.dumps({"status":"STANDARD_LIBRARY_SIMULATION_ONLY","runtime_instrumentation_board_verified":False,"dpu_jobs_executed":0,"camera_or_database_accessed":False,"recent_window_count":r["recent_count"],"cumulative_count":r["count"]}))
