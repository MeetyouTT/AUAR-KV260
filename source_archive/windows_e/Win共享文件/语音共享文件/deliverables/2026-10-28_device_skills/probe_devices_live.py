"""Actual camera, observation cadence and CPU VLM; no microphone or playback."""
import base64, hashlib, io, json, sys, time, urllib.request, uuid, wave
from pathlib import Path

H=Path(__file__).resolve().parent
AURA=H.parents[1]/'aura'
sys.path[:0]=[str(AURA),str(H.parent/'2026-10-18_board_dialogue'),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
from board_ssh import ssh
from tools.visual_voice_host import VisualReplyStream
c=json.loads((H/'candidate.json').read_text())

def get(url):
    with urllib.request.urlopen(url,timeout=5) as f:return json.load(f)

report={'scope':'deployed code, existing camera and real local models; no live speech or audible playback'}
assets=get('http://192.168.50.1:8792/v1/voice/social')['assets']
assert set(assets)=={'arrival','invitation'},'Selected voice social assets not ready'
report['social_assets']={}
for name,a in assets.items():
    with urllib.request.urlopen('http://192.168.50.1:8792/v1/voice/audio/'+a['sha256']+'.wav',timeout=5) as f:raw=f.read(1000001)
    assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256']
    with wave.open(io.BytesIO(raw)) as w:
        duration=w.getnframes()/w.getframerate()
    assert 0<duration<=5
    report['social_assets'][name]={'sha256':a['sha256'],'duration_seconds':duration,'bytes':len(raw),'played':False}

script=r'''
import base64,json,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,ROOT)
from board.runtime.device_observer import DeviceObserver
from board.runtime.visual_capture import current_frame
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def gate(s):
 assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY'
 assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
 assert not s['manual_pan']['automatic_following']
 assert s['manual_pan']['state']=='FAULT' and s['manual_pan']['pulse_us'] is None
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==BOOT
gate(state())
first,jpeg=current_frame(boot)
pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
observer=DeviceObserver(boot)
observer.enabled=True
try:
 time.sleep(35)
 status=observer.public()
 assert status['sent']>=2 and not status['error'],status
finally:observer.close()
time.sleep(8)
gate(state())
last,jpeg=current_frame(boot)
assert first['camera_epoch']==last['camera_epoch']
assert pid==subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
print(json.dumps({'observation':status,'camera_pid':pid,'camera_epoch':last['camera_epoch'],
 'first_frame_id':first['frame_id'],'frame':last,'jpeg_base64':base64.b64encode(jpeg).decode(),
 'listening':False,'microphone_opened':False,'motion_command':False}))
'''.replace('ROOT',repr(c['runtime']+'/aura')).replace('BOOT',repr(c['boot']))
v=json.loads(ssh('python3 -B -',script,timeout=60))
frame=v.pop('frame');image=v.pop('jpeg_base64');report.update(v)
body=json.dumps({'boot':c['boot'],'history':True}).encode()
req=urllib.request.Request('http://127.0.0.1:8812/v1/memory/recall',data=body,headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=3) as f:rows=json.load(f)['observations']
new=[r for r in rows if r['frame_id']>v['first_frame_id']]
assert len(new)>=2 and all(0<len(r['summary'])<=240 for r in new)
report['stored_observations']=[{k:r[k] for k in ('frame_id','age_seconds','current')} | {'summary_characters':len(r['summary'])} for r in new]
pcm=b'\0\0'*3200
meta={'protocol':'aura-asr-1','board_boot_id':c['boot'],'session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,
      'generation':1,'capture_id':'automatic-visual-protocol-test','sample_count':3200,
      'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':45000}
stream=VisualReplyStream(meta,'请用一句话说明你现在看见了什么。')
stream.accept({'context':meta,'token':stream.token,'frame':frame,'jpeg_base64':image})
started=time.monotonic();events=list(stream)
assert [k for k,_ in events]==['text','speech_ready','complete']
assert events[-1][1]['reply_text']==events[0][1]
report['actual_visual_answer']={'seconds':round(time.monotonic()-started,3),'answer_characters':len(events[0][1]),
 'frame_id':frame['frame_id'],'camera_epoch':frame['camera_epoch'],'token_correlated':True,
 'raw_image_saved':False,'speech_asr_tts_included':False,'metrics':stream.metrics}
report['hub']=get('http://127.0.0.1:8812/health')
assert report['hub']['speaker_ready'] and not report['hub']['visual_error']
report['status']='PASS'
(H/'devices_live_acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
