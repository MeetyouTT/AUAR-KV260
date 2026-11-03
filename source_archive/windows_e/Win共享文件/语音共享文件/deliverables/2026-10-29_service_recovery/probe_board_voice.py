"""Two real ARM-client requests using only public WAVs; RAM output, no ACK."""
import base64,hashlib,json,wave
from recovery_common import H,P,read,save,board,same_board,ssh
baseline=read('validation_board.json');same_board(board(),baseline)
assert read('endpoints.json')['status']=='PASS'
assert not (H/'voice_probe.json').exists(),'Preserve existing probe evidence'
audio={}
for label,path in [('official',P/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'),
 ('drawing',H.parent/'2026-10-29_chat_latency/public_drawing.wav')]:
 with wave.open(str(path),'rb') as source:
  assert (source.getframerate(),source.getnchannels(),source.getsampwidth())==(16000,1,2)
  pcm=source.readframes(source.getnframes())
 audio[label]={'pcm':base64.b64encode(pcm).decode(),'sha256':hashlib.sha256(pcm).hexdigest()}
script=r'''
import base64,hashlib,json,sys,time,urllib.request,uuid
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
sys.path.insert(0,ROOT+'/aura')
from board.runtime.audio.voice_channel import VoiceChannel
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:return json.load(r)
def safe():
 s=state();pan=s['manual_pan'];hf=s['handsfree_dialogue']
 assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='IDLE_READY'
 assert not hf['enabled'] and not hf['microphone_open'] and not pan['automatic_following']
 assert not any(pan.get(k) for k in ('busy','moving','active_motion','motion_active'))
safe();rows=[];session=uuid.uuid4().hex
for generation,(label,entry) in enumerate(AUDIO.items(),1):
 pcm=base64.b64decode(entry['pcm']);assert hashlib.sha256(pcm).hexdigest()==entry['sha256']
 context={'protocol':'aura-asr-1','board_boot_id':BOOT,'session_id':session,'request_id':uuid.uuid4().hex,
  'generation':generation,'capture_id':'public-service-recovery-'+label,'sample_count':len(pcm)//2,
  'pcm_sha256':entry['sha256'],'budget_ms':60000}
 started=time.monotonic();events={};digest=hashlib.sha256();end={}
 def receive(header,payload):
  events.setdefault(header['kind'],round((time.monotonic()-started)*1000,2))
  if header['kind']=='audio':digest.update(payload)
  if header['kind']=='end':end.update(header)
 client=VoiceChannel('192.168.50.1')
 try:result=client.exchange(context,pcm,receive)
 finally:client.close()
 assert result['network_complete'] and not result['playback_verified'] and result['sample_count']>0
 assert result['pcm_sha256']==digest.hexdigest()
 assert end['timing']['llm']['backend']=='ollama'
 rows.append({'label':label,'status':'PASS','input_sha256':entry['sha256'],'samples':result['sample_count'],
  'output_sha256':result['pcm_sha256'],'first_pcm_ms':events['audio'],'tts_cache_hits':end['tts_cache_hits'],
  'playback_ack_sent':False,'durable_conversation_used':False,
  'timing':{k:v for k,v in end['timing'].items() if k not in ('first_clause_text','conversation_context')}})
safe()
print(json.dumps({'status':'PASS','checks':rows,'microphone_opened':False,'physical_playback':False,
 'motion_command_sent':False,'board_boot':BOOT,'runtime':ROOT},ensure_ascii=True))
'''.replace('BOOT',repr(baseline['boot'])).replace('ROOT',repr(baseline['actual_runtime'])).replace('AUDIO',repr(audio))
report={'status':'STARTING'}
try:
 raw=ssh('python3 -B -',script,timeout=150);report=json.loads(raw.strip().splitlines()[-1]);assert report['status']=='PASS'
 same_board(board(),baseline)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
save('voice_probe.json',report)
print(json.dumps({'status':report['status'],'checks':len(report.get('checks',[])),
 'first_pcm_ms':[r['first_pcm_ms'] for r in report.get('checks',[])],'error':report.get('error')}))
raise SystemExit(0 if report['status']=='PASS' else 1)
