"""Actual ARM client: public PCM in RAM, wake routing and immediate replacement requests."""
import base64,hashlib,json,sys,wave
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
assert json.loads((H/'deployment_r8.json').read_text(encoding='utf-8'))['status']=='COMMITTED'
assert not (H/'live_handoff_r8_final.json').exists()
b=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
audio={}
for label,path in [('question',P/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'),
 ('wake',H.parent/'2026-10-28_device_skills/synthetic_wake_fixtures/name_only.wav'),
 ('nonwake',H.parent/'2026-10-28_device_skills/synthetic_wake_fixtures/ordinary_speech.wav'),
 ('tts_question',H/'public_tts_question.wav')]:
 with wave.open(str(path),'rb') as f:
  assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
  pcm=f.readframes(f.getnframes())
 audio[label]={'pcm':base64.b64encode(pcm).decode(),'sha256':hashlib.sha256(pcm).hexdigest()}
script=r'''
import base64,hashlib,json,sys,threading,time,urllib.request,uuid
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
sys.path.insert(0,ROOT+'/aura')
from board.runtime.audio.voice_channel import VoiceChannel
from common.handsfree_entry import EntryRejected
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:return json.load(r)
s=state();assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='IDLE_READY'
assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
assert s['manual_pan']['automatic_following'] is False and not s['manual_pan']['readback']['active']
def health():
 with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:return json.load(r)
h=health();assert h['ready'] and not h['busy'] and h['source_fingerprint']==FP
audio={k:base64.b64decode(v['pcm']) for k,v in AUDIO.items()}
generation=0;session=uuid.uuid4().hex;rows=[]
def context(label):
 global generation
 generation+=1;pcm=audio[label]
 return {'protocol':'aura-asr-1','board_boot_id':BOOT,'session_id':session,'request_id':uuid.uuid4().hex,
  'generation':generation,'capture_id':'public-handoff-'+label,'sample_count':len(pcm)//2,
  'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':60000}
for stage in ('text','tts','audio'):
 label='tts_question' if stage=='tts' else 'question'
 first=VoiceChannel('192.168.50.1');meta=context(label);stop=threading.Event()
 observed={'stage':stage,'request_id':meta['request_id'],'cancel_triggered':False,'audio_before_cancel':0}
 def receive(header,payload):
  if header['kind']=='audio':observed['audio_before_cancel']+=len(payload)//2
  if header['kind']==stage:
   observed['cancel_triggered']=True;first.cancel()
 def watch():
  until=time.monotonic()+20
  while not stop.is_set() and time.monotonic()<until:
   try:
    v=health()
    if v['dependencies']['tts'].get('request_active'):
     observed['cancel_triggered']=True;observed['tts_active_at_cancel']=True;first.cancel();return
   except Exception:pass
   stop.wait(.05)
  if not stop.is_set():observed['stage_timeout']=True;first.cancel()
 watcher=threading.Thread(target=watch,daemon=True) if stage=='tts' else None
 if watcher:watcher.start()
 try:
  first.exchange(meta,audio[label],receive)
  raise AssertionError('Expected cancellation before successful completion')
 except InterruptedError:observed['cancelled']=True
 finally:
  stop.set();first.close()
  if watcher:watcher.join(4)
 assert observed['cancel_triggered'] and not observed.get('stage_timeout'),observed
 second=VoiceChannel('192.168.50.1');next_meta=context('question');began=time.monotonic();digest=hashlib.sha256();end={}
 def next_frame(header,payload):
  if header['kind']=='audio':
   digest.update(payload)
   if 'first_pcm_ms' not in observed:observed['first_pcm_ms']=round((time.monotonic()-began)*1000,2)
  if header['kind']=='end':end.update(header)
 try:result=second.exchange(next_meta,audio['question'],next_frame)
 finally:second.close()
 assert result['network_complete'] and not result['playback_verified'] and result['sample_count']>0
 assert result['pcm_sha256']==digest.hexdigest()
 observed.update(status='PASS',next_request_id=next_meta['request_id'],next_generation=next_meta['generation'],
   next_sample_count=result['sample_count'],next_pcm_sha256=result['pcm_sha256'],playback_ack_sent=False,
   backend=end.get('timing',{}).get('llm',{}).get('backend'))
 rows.append(observed)
 print(json.dumps({'progress':observed},ensure_ascii=True),flush=True)
channel=VoiceChannel('192.168.50.1')
try:
 result=channel.exchange(context('wake'),audio['wake'],lambda *a:None,wake_entry=True)
 assert result=={'wake_only':True}
 rows.append({'stage':'wake_only','status':'PASS','playback_ack_sent':False})
finally:channel.close()
channel=VoiceChannel('192.168.50.1')
try:
 try:
  channel.exchange(context('nonwake'),audio['nonwake'],lambda *a:None,wake_entry=True)
  raise AssertionError('Background speech must not bypass wake gate')
 except EntryRejected:rows.append({'stage':'nonwake_rejected','status':'PASS','playback_ack_sent':False})
finally:channel.close()
until=time.monotonic()+5
while health()['busy'] and time.monotonic()<until:time.sleep(.05)
h=health();assert h['ready'] and not h['busy'] and not h['dependencies']['tts']['request_active']
assert h['voice_request_diagnostics']['counts'].get('busy',0)==0
assert h['voice_request_diagnostics']['counts'].get('expired',0)==0
s=state();assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
assert s['phase']=='IDLE' and not s['playing'] and s['manual_pan']['automatic_following'] is False
print(json.dumps({'status':'PASS','checks':rows,'voice_diagnostics':h['voice_request_diagnostics'],
 'mic_opened':False,'playback':False,'playback_ack_sent':False,'durable_conversation_used':False,
 'actual_boot':BOOT,'board_runtime':ROOT,'source_fingerprint':FP},ensure_ascii=True),flush=True)
'''.replace('BOOT',repr(b['boot'])).replace('ROOT',repr(b['actual_runtime'])).replace('FP',repr(json.loads((H/'source_plan_r8.json').read_text())['candidate_fingerprint'])).replace('AUDIO',repr(audio))
report={'status':'STARTING','mic_opened':False,'playback':False,'playback_ack_sent':False}
try:
 import textwrap
 script="import json,traceback\ntry:\n"+textwrap.indent(script,' ')+"\nexcept Exception as exc:\n print(json.dumps({'status':'FAIL','checks':globals().get('rows',[]),'error':type(exc).__name__+': '+str(exc),'trace':traceback.format_exc()},ensure_ascii=True),flush=True)\n"
 raw=ssh('python3 -B -',script,timeout=150)
 lines=raw.strip().splitlines()
 (H/'live_handoff_r8_final_network.log').write_text(raw,encoding='utf-8')
 report=json.loads(lines[-1])
 assert report['status']=='PASS' and len(report['checks'])==5
except Exception as exc:
 report['status']='FAIL'
 report.setdefault('error',type(exc).__name__+': '+str(exc))
 report['host_error']=type(exc).__name__+': '+str(exc)
(H/'live_handoff_r8_final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'checks':len(report.get('checks',[])),
 'first_pcm_ms':[r.get('first_pcm_ms') for r in report.get('checks',[]) if 'first_pcm_ms' in r],'error':report.get('error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
