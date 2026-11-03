import base64,hashlib,json,zlib
raw=zlib.decompress(base64.b64decode('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'))
assert hashlib.sha256(raw).hexdigest()=='001898f491e026120f668580d0547698bfcfb97d6e0ceb181d40e6e61a866f30'
exec(compile(raw,'pinned-idle-maintenance','exec'))

import importlib.util,sys,time,urllib.request
from pathlib import Path
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
ROOT=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura')
SOURCE=ROOT/'tools/gstreamer_persistent_engine.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='f257cf2d4cf9749b0d83d377d78c2b963d989496fdfe322131f7f476beb39d8c'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('_actual_persistent_for_dummy',SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    with op.open('http://127.0.0.1:8790/health',timeout=2) as f:s=json.load(f)
    return {'pid':s['pid'],'detected':s['detected_frames'],'camera_error':s['camera_error'],'detector_error':s['detector_error']}
before=health();pipelines=[]
def factory(gst,device):
    assert device=='SYNTHETIC_FAKESINK_NO_ALSA'
    pipeline=gst.parse_launch('appsrc name=source is-live=true format=time block=false caps=audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1 ! audioconvert ! fakesink name=sink sync=true')
    pipelines.append(pipeline)
    return pipeline,pipeline.get_by_name('source'),pipeline.get_by_name('sink')
class Engine(IdleMaintenanceEngine,base.PersistentGstAudioEngine):pass
engine=Engine.__new__(Engine);engine.configure_idle_maintenance(factory)
states=[];result={}
try:
    base.PersistentGstAudioEngine.__init__(engine,Gst,'SYNTHETIC_FAKESINK_NO_ALSA',pipeline_factory=factory)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        s=engine.poll()
        if s['device_ready']:break
        time.sleep(.02)
    else:raise RuntimeError('Synthetic initial sink position never became ready')
    first=engine.pipeline
    assert engine.command({'type':'stop','token':1}) and engine.pipeline is first
    seq=engine.reference_sequence
    args=dict(request_id='SYNTHETIC_REQUEST_1',expected_token=1,new_token=2,
        controller_idle=True,capture_idle=True,reference_idle=True,commands_pending=False)
    assert engine.request_idle_maintenance(**args)
    assert engine.request_idle_maintenance(**args)  # Same request cannot rebuild twice.
    assert engine.take_references()==[]
    assert not engine.command({'type':'stream','token':3})
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        s=engine.poll();state=s['maintenance_state']
        if not states or states[-1]!=state:states.append(state)
        if state=='READY_UNVERIFIED':break
        if state=='FAILED_HELD':raise RuntimeError('Synthetic maintenance failed: '+s['maintenance_reason'])
        time.sleep(.02)
    else:raise RuntimeError('Synthetic maintenance did not finish in bound')
    assert len(pipelines)==2 and engine.pipeline is not first and engine.pipeline_epoch==1
    assert first.get_state(0)[1]==Gst.State.NULL
    assert engine.token==2 and engine.reference_sequence>seq
    references=engine.take_references()
    assert references and all(x['pipeline_epoch']==1 and x['sequence']>seq for x in references)
    assert engine.request_idle_maintenance(**args) and len(pipelines)==2
    assert engine.command({'type':'close','token':3})
    assert not engine.command({'type':'stream','token':4})
    assert engine.take_references()==[]
    result={'scope':'REAL_GSTREAMER_SYNTHETIC_FAKESINK_LIFECYCLE_ONLY',
        'candidate_source_sha256':hashlib.sha256(raw).hexdigest(),'states':states,
        'null_before_rebuild_verified':True,'pipeline_epoch':engine.pipeline_epoch,
        'pipelines_created':len(pipelines),'reference_sequence_preserved':True,
        'duplicate_request_rebuilt_pipeline':False,'ordinary_stop_keeps_pipeline':True,
        'late_stream_after_close_refused':True,'gstreamer':Gst.version_string(),
        'alsa_opened':False,'camera_or_dpu_opened':False,'new_audio_recorded_or_played':False,
        'production_integration_verified':False,'mcp01_recovery_verified':False}
finally:
    for pipeline in pipelines:
        pipeline.set_state(Gst.State.NULL)
        assert pipeline.get_state(2*Gst.SECOND)[1]==Gst.State.NULL
after=health()
assert after['pid']==before['pid'] and after['detected']>before['detected']
assert not after['camera_error'] and not after['detector_error']
result.update(camera_before=before,camera_after=after,all_synthetic_pipelines_released=True)
print(json.dumps(result),flush=True)
