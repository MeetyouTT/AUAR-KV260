import base64,hashlib,json,zlib
raw=zlib.decompress(base64.b64decode('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'))
assert hashlib.sha256(raw).hexdigest()=='363a9a6ef228ed8c700b6db8a10cf0c374f3977e09ed04f685d21ca615a8623d'
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
