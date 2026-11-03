"""Audible isolated persistent-device probe; existing GUI/vision are preserved."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

names=['aura/tools/gstreamer_audio_engine.py','aura/tools/gstreamer_persistent_engine.py']
files={name:base64.b64encode((ROOT/name).read_bytes()).decode('ascii') for name in names}
release=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:12]
payload={'files':files,'release':release}
remote=r'''
import base64,hashlib,json,sys,time,urllib.request,wave
from pathlib import Path
payload=PAYLOAD
root=Path('/home/root/aura-stream-playback-20261018')/('probe-'+payload['release'])
root.mkdir(parents=True,exist_ok=True)
for name,value in payload['files'].items():
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value))
sys.path.insert(0,str(root/'aura'))
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
from tools.gstreamer_persistent_engine import PersistentGstAudioEngine
Gst.init(None)
def idle():
    u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
    return u['phase']=='IDLE' and not u['playing'] and u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('local_transcription',{}).get('service',{}).get('pending')
assert idle(),'Board is busy; playback not started'
clip=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/deliverables/2026-10-06_xilan_live/cache/56db1d9eab155c01596bb2fee2501cd37093f7052bb0f52150e4c426a887363c.wav')
raw=clip.read_bytes();sha=hashlib.sha256(raw).hexdigest()
with wave.open(str(clip),'rb') as audio:expected=audio.readframes(audio.getnframes());duration=audio.getnframes()/24000
report={'kind':'REAL_GSTREAMER_PLAYBACK_REQUIRES_LISTENING','gst':Gst.version_string(),'cases':[],
        'source_sha256':sha,'pcm_sha256':hashlib.sha256(expected).hexdigest(),'duration':duration,
        'board_services_modified':False,'model_on_board':False,'startup_warmup_seconds':1}
engine=PersistentGstAudioEngine(Gst,'hw:CARD=MCP01,DEV=0')
try:
    before=time.monotonic();deadline=before+8
    while not engine.poll()['device_ready']:
        assert not engine.error,engine.error
        if time.monotonic()>deadline:raise RuntimeError('Device did not warm')
        time.sleep(.01)
    report['warmup_ms']=round((time.monotonic()-before)*1000,2)
    for token in (1,2):
        assert idle(),'User interaction detected'
        requested=time.monotonic();engine.command({'type':'play','token':token,'path':str(clip),'sha256':sha})
        assert b''.join(item[0] for item in engine.queue)==expected,'PCM changed'
        samples=[];deadline=requested+duration+5;last_check=0
        while time.monotonic()<deadline:
            value=engine.poll()
            assert not value['error'],value['error']
            samples.append({'elapsed_ms':round((time.monotonic()-requested)*1000,2),**value})
            if time.monotonic()-last_check>.15:
                assert idle(),'User interaction detected';last_check=time.monotonic()
            if value['done']:break
            time.sleep(.01)
        else:raise RuntimeError('Persistent playback timeout')
        report['cases'].append({'token':token,'request_to_sink_start_ms':round((value['started_at']-requested)*1000,2),
             'elapsed_ms':round((time.monotonic()-requested)*1000,2),'content_clock':value['clock'],
             'device_remains_open':engine.pipeline is not None,'pcm_identical':True,'samples':samples})
        until=time.monotonic()+.8
        while time.monotonic()<until:engine.poll();time.sleep(.01)
finally:engine.release()
report['status']='PASS_SINK_CLOCK_ONLY_NOT_ACOUSTIC'
(root/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
'''.replace('PAYLOAD',repr(payload))
report=json.loads(ssh('python3 -',remote,timeout=55))
(HERE/'persistent_board.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:report[key] for key in ('status','warmup_ms','duration')},ensure_ascii=True))
print(json.dumps([{key:value for key,value in item.items() if key!='samples'} for item in report['cases']]))
