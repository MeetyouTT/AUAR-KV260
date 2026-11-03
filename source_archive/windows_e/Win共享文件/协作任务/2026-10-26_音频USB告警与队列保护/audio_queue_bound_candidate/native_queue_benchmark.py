"""Bounded real appsrc/fakesink stall test; opens no audio/USB device.

Each trial uses the actual reviewed engine with a real GStreamer appsrc. A
temporary source-pad BLOCK_DOWNSTREAM probe stops consumption. A wrapper
removes only this injected probe before state NULL so fault cleanup cannot
deadlock on the test itself. The controller limits its own child processes to
an overall eight-second budget; it never signals any business process.
"""
import argparse
import hashlib
import importlib.util
import json
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ORIGINAL_SHA='f257cf2d4cf9749b0d83d377d78c2b963d989496fdfe322131f7f476beb39d8c'
CANDIDATE_SHA='f5d987904aec0dc679936da27018f404f9cc77f42d300e0579a3b52a95f0655c'


def load(path,expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,'Engine SHA changed'
    spec=importlib.util.spec_from_file_location('native_queue_engine',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def worker(args):
    sys.path.insert(0,str(args.runtime_root))
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst
    Gst.init(None)
    entered=threading.Event();pipelines=[];probe=[None];pad=[None]
    phases=[]

    def remove_probe():
        if probe[0] is not None:
            pad[0].remove_probe(probe[0]);probe[0]=None

    class ControlledPipeline:
        def __init__(self,pipeline):self.pipeline=pipeline
        def __getattr__(self,name):return getattr(self.pipeline,name)
        def set_state(self,state):
            if state==Gst.State.NULL:
                remove_probe();phases.append('injected_probe_removed_before_NULL')
            return self.pipeline.set_state(state)

    def factory(gst,unused):
        pipeline=gst.parse_launch('appsrc name=source is-live=true format=time block=false max-bytes=7680 '
                                 '! fakesink name=sink sync=false async=false')
        source=pipeline.get_by_name('source');sink=pipeline.get_by_name('sink')
        source.set_property('caps',gst.Caps.from_string('audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1'))
        pipeline.use_clock(gst.SystemClock.obtain())
        pipelines.append(pipeline);pad[0]=source.get_static_pad('src')
        return ControlledPipeline(pipeline),source,sink

    path=args.baseline_engine if args.role=='baseline' else args.candidate_engine
    module=load(path,ORIGINAL_SHA if args.role=='baseline' else CANDIDATE_SHA)
    engine=None;source=None;records=[];max_poll_ms=0.;started=time.monotonic();result={}
    def stop_handler(signum,frame):raise SystemExit('owned benchmark terminated')
    signal.signal(signal.SIGTERM,stop_handler)
    try:
        engine=module.PersistentGstAudioEngine(Gst,'FAKESINK_NO_DEVICE',pipeline_factory=factory)
        source=engine.source
        warm_until=time.monotonic()+.15
        while time.monotonic()<warm_until:
            engine.poll();time.sleep(.005)
        assert engine.pipeline is not None and engine.pipeline.get_clock() is not None,'No live pipeline clock'
        def blocked(unused_pad,info):
            entered.set();return Gst.PadProbeReturn.OK
        probe[0]=pad[0].add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM,blocked)
        blocked_at=time.monotonic();maximum=0;reason='BOUNDED_TRIAL_COMPLETE'
        while time.monotonic()-blocked_at<2.24:
            tick=time.monotonic();snapshot=engine.poll();elapsed=(time.monotonic()-tick)*1000
            max_poll_ms=max(max_poll_ms,elapsed)
            level=int(source.get_property('current-level-bytes'));maximum=max(maximum,level)
            records.append(dict(elapsed_s=round(time.monotonic()-blocked_at,3),queue_bytes=level,
                                error=snapshot['error'],pipeline_released=engine.pipeline is None))
            if engine.pipeline is None:
                reason='ENGINE_EXPLICIT_FAULT_RELEASE';break
            time.sleep(.005)
        snapshot=engine.snapshot()
        result=dict(role=args.role,gst_version=Gst.version_string(),engine_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            reason=reason,injected_probe_entered=entered.is_set(),maximum_queue_bytes=maximum,
            nominal_max_bytes=7680,maximum_poll_ms=round(max_poll_ms,3),polls=len(records),
            snapshot=snapshot,pipeline_released_by_engine=engine.pipeline is None,
            appsrc_property_supported=True,alsa_opened=False,usb_opened=False,
            phases=phases,tail=records[-3:],elapsed_s=round(time.monotonic()-started,3))
    finally:
        remove_probe()
        if engine is not None:engine.release()
        for pipeline in pipelines:pipeline.set_state(Gst.State.NULL)
        if result:
            result['injected_probe_removed']=probe[0] is None
            result['cleanup_NULL_requested']=True
    print(json.dumps(result),flush=True)


def controller(args):
    began=time.monotonic();results=[]
    for role in ('baseline','candidate'):
        remaining=7.7-(time.monotonic()-began)
        if remaining<=.2:raise RuntimeError('Overall benchmark budget consumed')
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--role',role,
            '--runtime-root',str(args.runtime_root),'--baseline-engine',str(args.baseline_engine),
            '--candidate-engine',str(args.candidate_engine)]
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            stdout,stderr=child.communicate(timeout=min(3.6,remaining))
        except subprocess.TimeoutExpired:
            child.terminate()
            try:stdout,stderr=child.communicate(timeout=.1)
            except subprocess.TimeoutExpired:
                child.kill();stdout,stderr=child.communicate(timeout=.1)
            raise RuntimeError('Own benchmark child exceeded bounded timeout: '+role)
        assert child.returncode==0,(role,stderr[-800:])
        row=json.loads(stdout);results.append(row)
    before,after=results
    assert before['injected_probe_entered'] and after['injected_probe_entered']
    assert before['maximum_queue_bytes']>7680 and not before['pipeline_released_by_engine']
    assert after['maximum_queue_bytes']<=7680 and after['pipeline_released_by_engine']
    assert 'remained full' in after['snapshot']['error']
    assert all(row['injected_probe_removed'] and row['cleanup_NULL_requested'] for row in results)
    print(json.dumps(dict(status='REAL_APPSRC_QUEUE_BOUND_PASS',elapsed_s=round(time.monotonic()-began,3),
        results=results,device_opened=False,business_processes_changed=False,
        scope='real Gst appsrc/fakesink with injected downstream block; not USB/ALSA/acoustic or root-cause evidence'),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--baseline-engine',type=Path,required=True)
    parser.add_argument('--candidate-engine',type=Path,default=Path(__file__).with_name('gstreamer_persistent_engine.py'))
    parser.add_argument('--role',choices=('baseline','candidate'))
    args=parser.parse_args()
    if args.role:worker(args)
    else:controller(args)
