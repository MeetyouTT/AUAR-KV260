"""Actual ASR/27B/OmniVoice benchmark; same public WAVs, no mic/playback/durable memory."""
import argparse,datetime,hashlib,json,statistics,subprocess,sys,time,traceback,urllib.request,uuid,wave
from pathlib import Path
from types import SimpleNamespace
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from board.runtime.audio.voice_channel import VoiceChannel
from common.spoken_input import prepare_spoken_input
from tools.dialogue_stream import stream_body
from common.conversation_context import request_cost
from common import timeline
from tools.memory_timeline_host import memory_context,live_context
p=argparse.ArgumentParser();p.add_argument('phase',choices=['refined']);args=p.parse_args()
output=H/('voice_'+args.phase+'.json');assert not output.exists()
plan=json.loads((H/'source_plan_r8.json').read_text(encoding='utf-8'))
expected=plan['candidate_fingerprint']
def health():
 with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as r:return json.load(r)
def other_models():
 out={}
 for port in (11434,11435):
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/ps',timeout=5) as r:data=json.load(r)
  out[str(port)]=[{k:v for k,v in m.items() if k in ('name','digest','size','size_vram','context_length')} for m in data['models']]
 return out
first=health();assert first['ready'] and not first['busy'] and first['source_fingerprint']==expected
config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
spec=[('official',A/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav',None),
 ('tired',H/'public_tired.wav','我今天有点累，陪我聊聊'),
 ('weekend',H/'public_weekend.wav','周末想轻松一下，帮我想一个小活动'),
 ('drawing',H/'public_drawing.wav','我正在学画画，鼓励我一下')]
for label,path,text in spec+[('warmup',H/'public_warmup.wav','你好，今天想和我聊什么')]:
 if not path.exists():
  assert text
  subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(H/'synthesize_question.ps1'),'-Text',text,'-OutputPath',str(path)],
   capture_output=True,check=True,timeout=20)
def exchange(label,path):
 v=health();assert v['ready'] and not v['busy'] and v['source_fingerprint']==expected
 with wave.open(str(path),'rb') as f:
  assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
  pcm=f.readframes(f.getnframes())
 meta={'protocol':'aura-asr-1','board_boot_id':'public-latency-benchmark','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,
  'generation':1,'capture_id':'public-latency-'+label,'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
 begun=time.perf_counter();events={};digest=hashlib.sha256();end={};transcript='';segments={};play_end=None;gap_ms=0
 def receive(header,payload):
  nonlocal transcript,play_end,gap_ms
  ms=round((time.perf_counter()-begun)*1000,2);kind=header['kind'];events.setdefault(kind,ms)
  if kind=='transcript':transcript=header['text']
  if kind=='audio':
   digest.update(payload)
   segment=segments.setdefault(str(header['segment_id']),{'first_ms':ms,'samples':0})
   segment['samples']+=len(payload)//2
   if play_end is None:play_end=ms
   elif ms>play_end:gap_ms+=ms-play_end;play_end=ms
   play_end+=len(payload)/2/24000*1000
  if kind=='end':end.update(header)
 channel=VoiceChannel('192.168.50.1')
 try:result=channel.exchange(meta,pcm,receive)
 finally:channel.close()
 assert result['network_complete'] and not result['playback_verified'] and result['sample_count']>0 and result['pcm_sha256']==digest.hexdigest()
 timing=end['timing'];assert 'conversation_context' not in timing
 gate=getattr(timeline,'recall_requested',timeline.historical)
 wants_history=gate(transcript)
 stub=SimpleNamespace(timeline_zone='America/Los_Angeles')
 model_text=prepare_spoken_input(transcript)['text']
 if wants_history:
  used,maximum=request_cost(config['model'],[],model_text)
  observation=memory_context(stub,meta,transcript,max_bytes=min(2600,max(0,maximum-used-32)))
 else:observation=live_context(stub,meta,transcript)
 history=[]
 if observation is not None:
  used,maximum=request_cost(config['model'],[observation],model_text)
  if used<=maximum:history=[observation]
 assert timing['history_messages']==len(history),(timing['history_messages'],len(history))
 body=stream_body(config['model'],history,model_text,reply_first=True,think=False)
 if timing['llm'].get('quality_retry_count')==1:
  body['messages'][0]['content']+='刚才的台词只复制了用户的问题。请直接回答对方的问题，不要校对或复述输入。'
 expected_hash=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 if args.phase=='refined':assert timing['llm']['request_sha256']==expected_hash
 return {'label':label,'input_wav_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'context':meta,'transcript':transcript,
  'reply':result['reply_text'],'first_text_ms':events.get('text'),'first_pcm_ms':events['audio'],'total_ms':round((time.perf_counter()-begun)*1000,2),
  'sample_count':result['sample_count'],'pcm_sha256':result['pcm_sha256'],'timing':timing,'clauses':end['clauses'],
  'tts_cache_hits':end['tts_cache_hits'],'segments':segments,'estimated_delivery_starvation_ms':round(gap_ms,2),
  'expected_request_sha256':expected_hash,'supplemental_context_messages':len(history),
  'timeline_lookup_requested':wants_history,'playback_ack_sent':False}
report={'status':'RUNNING','phase':args.phase,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'revision':first['service_revision'],'fingerprint':expected,'models_before':other_models(),
 'context_contract':{'conversation_history':[],'facts':[],'visual_boot_cache':'foreign public boot',
                     'timeline_context':'reconstructed per routing; never copied to this report','durable_conversation':False},
 'mic_opened':False,'playback':False,'tts_steps':16,'trials':[]}
def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
save()
try:
 report['unscored_warmup']=exchange('warmup',H/'public_warmup.wav');save()
 for repeat in range(2):
  for label,path,text in spec:
   row=exchange(label,path);row['repeat']=repeat;report['trials'].append(row);save()
   print(json.dumps({'phase':args.phase,'label':label,'repeat':repeat,'first_pcm_ms':row['first_pcm_ms'],'tts_cache_hits':row['tts_cache_hits'],
    'clauses':row['clauses'],'supply_gap_ms':row['estimated_delivery_starvation_ms']},ensure_ascii=True),flush=True)
 report['models_after']=other_models();assert report['models_before']==report['models_after'],'Model residency changed during measurement'
 v=health();assert v['ready'] and not v['busy']
 report.update(status='PASS',median_first_pcm_ms=statistics.median(r['first_pcm_ms'] for r in report['trials']),
  median_first_text_ms=statistics.median(r['first_text_ms'] for r in report['trials']),
  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc),trace=traceback.format_exc())
finally:save()
print(json.dumps({'status':report['status'],'phase':args.phase,'median_first_pcm_ms':report.get('median_first_pcm_ms'),'error':report.get('error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
