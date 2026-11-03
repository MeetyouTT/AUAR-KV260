"""Reproduce native-queue semantics using reviewed engines and a fake source.

This does not load GStreamer or access USB/ALSA. The source returns OK while
retaining buffers; the pipeline clock advances and the sink position is fixed.
"""
import json
from test_appsrc_queue_bound import Rig,old,new


def replay(module,seconds):
    rig=Rig(module)
    try:
        rig.source.drain=False
        rig.advance(seconds,sink_moves=False)
        return dict(seconds=seconds,pushed_buffers=len(rig.source.pushes),
            queued_bytes=rig.source.level,nominal_max_bytes=7680,
            python_queue_length=len(rig.engine.queue),
            python_interval_length=len(rig.engine.intervals),
            pipeline_released=rig.engine.pipeline is None,
            snapshot=rig.engine.snapshot())
    finally:rig.engine.release()


if __name__=='__main__':
    print(json.dumps(dict(scope=__doc__,before_2_seconds=replay(old,2),
        after_2_seconds=replay(new,2),after_3_seconds=replay(new,3)),indent=2))
