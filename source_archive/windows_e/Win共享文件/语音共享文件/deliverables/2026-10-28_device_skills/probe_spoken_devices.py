"""Synthetic speech -> actual ARM wire client -> ASR / VLM / selected TTS, no playback."""
import argparse,base64,json,sys,wave
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text());rows=json.loads((H/'wake_phrases.json').read_text(encoding='utf-8'))
parser=argparse.ArgumentParser();parser.add_argument('--only');parser.add_argument('--output',default='spoken_devices_acceptance.json');args=parser.parse_args()
assert Path(args.output).name==args.output
if args.only:rows=[r for r in rows if r['id']==args.only]
assert rows
for row in rows:
 with wave.open(str(H/'synthetic_wake_fixtures'/(row['id']+'.wav'))) as f:
  assert (f.getnchannels(),f.getframerate(),f.getsampwidth())==(1,16000,2)
  raw=f.readframes(f.getnframes())
 row['pcm']=base64.b64encode(raw).decode()
script=r'''
import base64,hashlib,http.client,json,sys,time,urllib.request,uuid
from pathlib import Path
sys.path.insert(0,ROOT)
from board.runtime.audio.voice_channel import VoiceChannel
from common.asr_wire import encode_context
from common.handsfree_entry import EntryRejected
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==BOOT
def gate():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
 assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY'
 assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
 assert not s['manual_pan']['automatic_following']
gate();results=[];session=uuid.uuid4().hex
for n,row in enumerate(ROWS):
 pcm=base64.b64decode(row['pcm']);item={k:v for k,v in row.items() if k!='pcm'}
 item['input_pcm_sha256']=hashlib.sha256(pcm).hexdigest()
 meta={'protocol':'aura-asr-1','board_boot_id':boot,'session_id':session,'request_id':uuid.uuid4().hex,
   'generation':n,'capture_id':row['id'],'sample_count':len(pcm)//2,'pcm_sha256':item['input_pcm_sha256'],'budget_ms':120000}
 if row['expected']=='memory_answer':
  req=urllib.request.Request('http://192.168.50.1:8812/v1/memory/recall',data=json.dumps({'boot':boot,'history':True}).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=3) as f:observations=json.load(f)['observations']
  assert observations,'Memory integration requires actual prior observations'
  item['prior_observation_ages_seconds']=[o['age_seconds'] for o in observations]
 conn=http.client.HTTPConnection('192.168.50.1',8791,timeout=10)
 try:
  conn.request('POST','/v1/asr/transcribe',pcm,{'X-Aura-Asr':encode_context(meta),'Content-Type':'application/octet-stream'})
  response=conn.getresponse();assert response.status==200
  item['actual_asr']=json.loads(response.read())['text']
 finally:conn.close()
 ch=VoiceChannel('192.168.50.1',visual_question=True);events=[];audio=bytearray();started=time.monotonic()
 def receive(h,p):
  kind=h['kind']
  if kind=='transcript' and h.get('visual_request'):
   ch.visual_frame(meta,h['visual_request']);item['visual_frame_upload']=True
  if kind=='audio':
   audio.extend(p);item.setdefault('first_audio_ms',round((time.monotonic()-started)*1000,2))
  if kind=='end':item['response_backend']=h.get('timing',{}).get('llm',{}).get('backend')
  events.append(kind)
 try:
  result=ch.exchange(meta,pcm,receive,wake_entry=row['expected'] not in ('visual_answer','device_answer','memory_answer'))
  if result.get('wake_only'):item['outcome']='wake_only'
  else:
   assert result['network_complete'] and not result['playback_verified']
   assert hashlib.sha256(audio).hexdigest()==result['pcm_sha256'] and len(audio)>0
   item.update(outcome='answer',samples=len(audio)//2,reply_characters=len(result['reply_text']))
   if row['expected']=='device_answer':item['device_reply_expected']='还没有登记声纹' in result['reply_text']
   if row['expected']=='memory_answer':
    item['past_tense_wording']=any(w in result['reply_text'] for w in ('刚才','之前','先前','当时','看到过'))
    item['current_picture_requested']=bool(item.get('visual_frame_upload'))
 except EntryRejected:item['outcome']='reject'
 except Exception as exc:item.update(outcome='error',error=type(exc).__name__+': '+str(exc)[:200])
 finally:ch.close()
 expected=row['expected']
 if expected in ('wake_only','reject','answer'):ok=item['outcome']==expected
 elif expected=='visual_answer':ok=item['outcome']=='answer' and item.get('visual_frame_upload')
 elif expected=='memory_answer':ok=item['outcome']=='answer' and not item.get('visual_frame_upload') and item.get('response_backend')=='ollama'
 else:ok=item['outcome']=='answer' and item.get('device_reply_expected')
 item.update(status='PASS' if ok else 'FAIL',events=sorted(set(events)),seconds=round(time.monotonic()-started,3))
 results.append(item)
gate()
print(json.dumps({'status':'PASS' if all(x['status']=='PASS' for x in results) else 'PARTIAL',
 'scope':'Microsoft Huihui synthetic PCM, actual deployed ARM client, ASR/VLM/LLM/TTS; no live mic, no playback, no playback ACK',
 'boot':boot,'checks':results,'microphone_opened':False,'motor_command':False,'no_private_memory_grants':True}))
'''.replace('ROOT',repr(c['runtime']+'/aura')).replace('BOOT',repr(c['boot'])).replace('ROWS',repr(rows))
v=json.loads(ssh('python3 -B -',script,timeout=200))
(H/args.output).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=True))
