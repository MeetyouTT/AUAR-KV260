"""Prepare real Gst lifecycle checks using only a synthetic fakesink."""
import ast,base64,hashlib,json,zlib
from pathlib import Path

root=Path(__file__).resolve().parent
raw=(root/'idle_maintenance_engine.py').read_bytes()
blob=base64.b64encode(zlib.compress(raw,9)).decode()
prefix="import base64,hashlib,json,zlib\nraw=zlib.decompress(base64.b64decode(%r))\nassert hashlib.sha256(raw).hexdigest()==%r\nexec(compile(raw,'pinned-idle-maintenance','exec'))\n" % (blob,hashlib.sha256(raw).hexdigest())
body=r'''
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
'''
source=prefix+body;ast.parse(source)
out=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_audio_maintenance_dummy_20261022_v2.py')
if out.exists():assert out.read_text()==source,'Use a new revision for changed board source'
else:out.write_text(source)
print(json.dumps({'source':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size}))
