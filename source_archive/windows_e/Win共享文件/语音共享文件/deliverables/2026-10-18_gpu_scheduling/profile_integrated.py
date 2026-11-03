"""Actual channel pipeline ABBA, same free-generation input/seed and uncached TTS."""
import hashlib,io,json,sys,time,statistics,uuid,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools.selected_voice_service import VoiceWorker
from tools import dialogue_stream
from tools.voice_channel_source import channel_frames
from common.voice_channel import read_frame,ChannelState
TEXT='今天比较开心，陪我聊聊'
EXPECTED='好呀，快跟我说说，是有什么好事发生啦？'
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
report={'actual_llm':True,'actual_tts':True,'actual_playback':False,'free_generation':True,'input':TEXT,'seed':42,'cases':[]}
worker=VoiceWorker(HERE/'benchmark_integrated_voice',python=sys.executable,model_path=ROOT/'aura/models/tts/OmniVoice',engine='omnivoice')
original=dialogue_stream.stream_body
def seeded(*args,**kwargs):
 body=original(*args,**kwargs);body['options']['seed']=42;return body
try:
 worker.warmup();assert worker.ready,worker.error
 with patch.object(dialogue_stream,'stream_body',seeded):
  # Prime both client paths; discovery is a startup cost, excluded from these
  # warm steady-state cases but retained in native_validation.json.
  for compact in (False,True):
   stream=dialogue_stream.OllamaReplyStream('http://127.0.0.1:11435',MODEL,[],TEXT,90,reply_first=True,compact_grammar=compact)
   for _ in stream:pass
  for index,compact in enumerate((False,True,True,False)):
   variant='compact' if compact else 'ollama'
   key,_=worker.synth.identity(EXPECTED)
   for suffix in ('.wav','.json'):
    target=worker.cache/(key+suffix);assert target.resolve().parent==worker.cache.resolve()
    if target.exists():target.unlink()
   models=SimpleNamespace(voice=worker,histories={},latency_options={'reply_first':True,'early_sentence':True,'coalesce_chat':True,'reuse_history':True,'compact_grammar':compact})
   meta={'protocol':'aura-asr-1','board_boot_id':'scheduling-benchmark','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'benchmark-'+uuid.uuid4().hex,'generation':1,'sample_count':3200,'pcm_sha256':hashlib.sha256(b'\x01\x00'*3200).hexdigest(),'budget_ms':120000}
   state=ChannelState(meta);pcm=bytearray();start=time.perf_counter();row={'variant':variant,'actual_playback':False,'playback_ack_sent':False}
   for packet in channel_frames(models,meta,TEXT,120,model=MODEL,host='http://127.0.0.1:11435'):
    header,raw=read_frame(io.BytesIO(packet));state.accept(header,raw)
    if header['kind']=='error':raise RuntimeError(header['error'])
    if header['kind']=='audio':
     pcm.extend(raw);row.setdefault('first_pcm_ms',round((time.perf_counter()-start)*1000,2))
    if header['kind']=='end':row['end']=header
   assert state.ended and state.text==EXPECTED,state.text
   assert row['end']['tts_cache_hits']==0 and row['end']['clauses']==1
   assert row['end']['timing']['llm']['quality_retry_count']==0
   assert row['end']['timing']['llm']['backend']==('llama_native_compact' if compact else 'ollama')
   output=HERE/('integrated-'+str(index)+'-'+variant+'.wav')
   with wave.open(str(output),'wb') as audio:audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(pcm)
   row.update(reply=state.text,audio_sha256=hashlib.sha256(pcm).hexdigest(),audio_path=str(output))
   report['cases'].append(row)
   (HERE/'integrated_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
   print(json.dumps({'variant':variant,'first_pcm_ms':row['first_pcm_ms'],'tts_ms':row['end']['tts_total_ms'],'preparation_ms':row['end']['timing']['llm']['request_preparation_ms'],'reply':state.text},ensure_ascii=True),flush=True)
 report['summary']={v:{'first_pcm_ms':round(statistics.median(r['first_pcm_ms'] for r in report['cases'] if r['variant']==v),2),'tts_ms':round(statistics.median(r['end']['tts_total_ms'] for r in report['cases'] if r['variant']==v),2)} for v in ('ollama','compact')}
 report['audio_bit_identical']=len({r['audio_sha256'] for r in report['cases']})==1
 (HERE/'integrated_profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'summary':report['summary'],'audio_bit_identical':report['audio_bit_identical']}),flush=True)
finally:worker.close()
