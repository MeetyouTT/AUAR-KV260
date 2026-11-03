"""Same-text, uncached same-voice ABBA: schema versus compact grammar overlap."""
import hashlib,http.client,json,sys,time,statistics,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.selected_voice_service import VoiceWorker
from tools.dialogue_stream import ReplyDecoder,REPLY_FIRST_FIELDS,stream_body
TEXT='还好呀，就是有点想你。你那边怎么样？'
report={'actual_llm':True,'actual_tts':True,'actual_playback':False,'fixed_reply_for_experiment':TEXT,'production_prompt_changed':False,'cases':[]}
worker=VoiceWorker(HERE/'benchmark_grammar_voice',python=sys.executable,model_path=ROOT/'aura/models/tts/OmniVoice',engine='omnivoice')
def post(path,data):
 with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:51742'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=10) as r:return json.load(r)
original=stream_body('aura-qwen3.8-27b-abliterated:iq4_xs',[],'你好汐蓝今天过得怎么样',reply_first=True)
prompt=post('/apply-template',{'messages':original['messages'],'chat_template_kwargs':{'enable_thinking':False},'enable_thinking':False,'add_generation_prompt':True})['prompt']
schema=json.loads(json.dumps(original['format']));schema['properties']['a']={'type':'string','const':TEXT}
grammar='root ::= '+json.dumps('{"a":'+json.dumps(TEXT,ensure_ascii=False)+',"b":',ensure_ascii=False)+' emotion '+json.dumps(',"c":""}')+'\n'+r'emotion ::= "\"neutral\"" | "\"friendly\"" | "\"happy\"" | "\"sad\""'+'\n'
try:
 worker.warmup();assert worker.ready,worker.error
 for index,variant in enumerate(('schema','compact','compact','schema')):
  body={'prompt':prompt,'stream':True,'n_predict':120,'temperature':.6,'top_k':20,'top_p':.95,'min_p':0.,'repeat_penalty':1.,'seed':42,'cache_prompt':True,'n_keep':4}
  body['grammar' if variant=='compact' else 'json_schema']=grammar if variant=='compact' else schema
  key,_=worker.synth.identity(TEXT)
  for suffix in ('.wav','.json'):
   target=worker.cache/(key+suffix);assert target.resolve().parent==worker.cache.resolve()
   if target.exists():target.unlink()
  decoder=ReplyDecoder(field_names=REPLY_FIRST_FIELDS);row={'variant':variant,'request':body}
  conn=http.client.HTTPConnection('127.0.0.1',51742,timeout=90);start=time.perf_counter()
  try:
   conn.request('POST','/completion',json.dumps(body).encode(),{'Content-Type':'application/json'})
   response=conn.getresponse();assert response.status==200,response.read(2000)
   while True:
    line=response.readline(32769);assert line and len(line)<=32768
    if not line.startswith(b'data:'):continue
    packet=json.loads(line[5:]);assert not packet.get('error'),packet
    decoder.feed(packet.get('content') or '')
    if 'reply_text' in decoder.values and 'speech_ready_ms' not in row:
     row['speech_ready_ms']=round((time.perf_counter()-start)*1000,2);assert decoder.values['reply_text']==TEXT
     tts_start=time.perf_counter();audio=worker.generate(TEXT)
     assert not audio['cache_hit']
     row.update(tts_ms=round((time.perf_counter()-tts_start)*1000,2),first_pcm_ms=round((time.perf_counter()-start)*1000,2))
    if packet.get('stop'):
     row.update(reply=decoder.finish(),raw_reply=decoder.buffer,timings=packet.get('timings'),tokens_predicted=packet.get('tokens_predicted'),total_ms=round((time.perf_counter()-start)*1000,2));break
  finally:conn.close()
  data=Path(audio['path']).read_bytes();output=HERE/('grammar-'+str(index)+'-'+variant+'.wav');output.write_bytes(data)
  row.update(audio_sha256=hashlib.sha256(data).hexdigest(),audio_path=str(output),audio_duration_seconds=audio['duration_seconds'])
  report['cases'].append(row)
  (HERE/'grammar_pipeline_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({k:row[k] for k in ('variant','speech_ready_ms','tts_ms','first_pcm_ms','total_ms','tokens_predicted','audio_sha256')},ensure_ascii=True),flush=True)
 report['summary']={v:{k:round(statistics.median(c[k] for c in report['cases'] if c['variant']==v),2) for k in ('speech_ready_ms','tts_ms','first_pcm_ms','total_ms','tokens_predicted')} for v in ('schema','compact')}
 report['audio_bit_identical']=len({c['audio_sha256'] for c in report['cases']})==1
 (HERE/'grammar_pipeline_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'summary':report['summary'],'audio_bit_identical':report['audio_bit_identical']}),flush=True)
finally:worker.close()
