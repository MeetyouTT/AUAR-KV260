"""Public direct-LLM probe. No service/source edits, microphone, TTS or persistent memory."""
import argparse,copy,datetime,hashlib,json,sys,time
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from tools import dialogue_stream as ds
config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
p=argparse.ArgumentParser();p.add_argument('variant',choices=['baseline','compact']);p.add_argument('label');p.add_argument('--question',default='对我做了介绍啊那么我想说的是呢大家如果对我的研究感兴趣呢嗯')
p.add_argument('--seed',type=int,default=8701);args=p.parse_args()
output=H/('llm_'+args.label+'.json');assert not output.exists()
original=ds.stream_body;requests=[];stream=None
def body(*a,**kw):
 value=copy.deepcopy(original(*a,**kw));value['options']['seed']=args.seed
 if args.variant=='compact':value['messages'][0]['content']+='只输出紧凑的单行JSON，符号周围不添加空格或换行；台词内容和三个字段要求保持。'
 actual=copy.deepcopy(value)
 if stream is not None and getattr(stream,'_repair_prompt',''):actual['messages'][0]['content']+=stream._repair_prompt
 requests.append({'sha256':hashlib.sha256(json.dumps(actual,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
  'body':actual})
 return value
report={'status':'RUNNING','variant':args.variant,'question':args.question,'seed':args.seed,
 'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'events':[]}
began=time.perf_counter()
try:
 with patch('tools.dialogue_stream.stream_body',body):
  stream=ds.OllamaReplyStream(config['ollama_host'],config['model'],[],args.question,60,reply_first=True,compact_grammar=False)
  for kind,value in stream:
   ms=round((time.perf_counter()-began)*1000,2)
   if kind not in [r['kind'] for r in report['events']]:report['events'].append({'kind':kind,'ms':ms})
   if kind=='complete':report['reply']=value
  report.update(status='PASS',metrics=stream.metrics,raw_json=stream.raw_reply)
 raw=report['raw_json'];minimal=json.dumps(json.loads(raw),ensure_ascii=False,separators=(',',':'))
 report['serialization_extra_characters']=len(raw)-len(minimal)
 report['requests']=requests;report['total_ms']=round((time.perf_counter()-began)*1000,2)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc),requests=requests)
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report.get(k) for k in ('status','variant','reply','events','serialization_extra_characters','metrics','error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
