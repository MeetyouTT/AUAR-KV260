"""Same PCM, board playback A/B: original versus 300ms device-start lead-in."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
SCRIPT=r'''
import hashlib,json,sys,time,urllib.request,wave
from pathlib import Path
root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
sys.path.insert(0,str(root/'aura'))
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
from tools.gstreamer_audio_engine import GstAudioEngine
Gst.init(None)
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
def idle(u):return u['phase']=='IDLE' and not u['playing'] and u['local_recording']['state']!='RECORDING' and not u['local_transcription']['service']['pending']
u=state()
assert idle(u),'Board busy; no playback started'
assert not u['ui_settings']['muted'],'Board muted'
folder=Path('/home/root/aura-audio-clarity-20261018');folder.mkdir(exist_ok=True)
original=root/'deliverables/2026-10-06_xilan_live/cache/56db1d9eab155c01596bb2fee2501cd37093f7052bb0f52150e4c426a887363c.wav'
with wave.open(str(original),'rb') as w: params=w.getparams();pcm=w.readframes(w.getnframes())
padded=folder/'same_pcm_leadin_300ms.wav'
with wave.open(str(padded),'wb') as w:w.setparams(params);w.writeframes(bytes(7200*2)+pcm)
with wave.open(str(padded),'rb') as w:assert w.readframes(w.getnframes())[14400:]==pcm
report={'kind':'PHYSICAL_PLAYBACK_AB_REQUIRES_USER_LISTENING','input_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'pcm_after_300ms_identical':True,'cases':[],'ui_before':{'phase':u['phase'],'settings':u['ui_settings']}}
engine=GstAudioEngine(Gst,'hw:CARD=MCP01,DEV=0')
try:
 for token,label,file in ((1,'A_original',original),(2,'B_same_pcm_plus_300ms_leadin',padded)):
  assert idle(state()),'Board user interaction started; stopping diagnostic'
  before=time.monotonic();engine.command({'type':'play','token':token,'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
  samples=[];warnings=[];deadline=time.monotonic()+12
  while time.monotonic()<deadline:
   v=engine.poll();samples.append({'wall':round(time.monotonic()-before,4),**v})
   if v['error']:raise RuntimeError(v['error'])
   if engine.bus:
    msg=engine.bus.timed_pop_filtered(0,Gst.MessageType.WARNING)
    if msg:
     err,debug=msg.parse_warning();warnings.append(str(err))
   if v['done']:break
   if not idle(state()):engine.release();raise RuntimeError('User interaction started; diagnostic stopped')
   time.sleep(.04)
  else:raise RuntimeError('Playback did not finish')
  report['cases'].append({'label':label,'file':str(file),'elapsed_seconds':round(time.monotonic()-before,3),'warnings':warnings,'samples':samples})
  time.sleep(1.2)
finally:engine.release()
report['ui_after']=state()['phase']
(folder/'playback_ab.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
'''
report=json.loads(ssh('python3 -',SCRIPT,timeout=40))
HERE=Path(__file__).resolve().parent
(HERE/'board_playback_ab.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'kind':report['kind'],'pcm_identical':report['pcm_after_300ms_identical'],'cases':[{'label':r['label'],'elapsed_seconds':r['elapsed_seconds'],'warnings':r['warnings']} for r in report['cases']],'ui_after':report['ui_after']}))
