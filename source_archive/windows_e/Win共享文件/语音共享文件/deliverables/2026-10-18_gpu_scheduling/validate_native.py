"""Real compact-route memory, explicit transformations and injected-copy repair."""
import json,sys,time,urllib.request
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools import dialogue_stream,native_grammar
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
report={'actual_llm':True,'actual_tts':False,'actual_playback':False,'turns':[],'extra_tasks':[]}
def save():
 (HERE/'native_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def run(text,history=None,inject_copy=False):
 with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as r:assert not json.load(r)['busy']
 original=dialogue_stream.stream_body;prepare=native_grammar.prepare
 def seeded(*args,**kwargs):
  body=original(*args,**kwargs);body['options']['seed']=42;return body
 def injected(host,body,timeout,cancelled):
  target,request,diagnostics=prepare(host,body,timeout,cancelled)
  if inject_copy and '刚才的台词只复制了用户的问题' not in body['messages'][0]['content']:
   wrong=json.dumps({'a':'汐蓝今天过得怎么样','b':'friendly','c':''},ensure_ascii=False,separators=(',',':'))
   request['grammar']='root ::= '+json.dumps(wrong,ensure_ascii=False)+'\n'
  return target,request,diagnostics
 stream=dialogue_stream.OllamaReplyStream('http://127.0.0.1:11435',MODEL,history or [],text,90,reply_first=True,compact_grammar=True)
 record={'input':text,'history_messages':len(history or []),'copy_fault_injected':inject_copy};start=time.perf_counter();emitted=''
 with patch.object(dialogue_stream,'stream_body',seeded),patch.object(native_grammar,'prepare',injected):
  for kind,value in stream:
   elapsed=round((time.perf_counter()-start)*1000,2)
   if kind=='text':emitted+=value;record.setdefault('first_delivered_ms',elapsed)
   if kind=='speech_ready':record['speech_ready_ms']=elapsed
   if kind=='complete':record.update(reply=value,raw_reply=stream.raw_reply,metrics=stream.metrics,total_ms=elapsed)
 assert emitted==record['reply']['reply_text'] and record['metrics']['backend']=='llama_native_compact'
 return record
history=[]
for question in ['我叫小林，喜欢蓝色，请记住。','我现在改成喜欢绿色了，不喜欢红色。',
                 '今天想聊些轻松的事情。','我说的数字是十五，不是五十。',
                 '我叫什么，喜欢什么颜色，说过的数字是多少？']:
 row=run(question,history);report['turns'].append(row)
 history=(history+[{'role':'user','content':question},{'role':'assistant','content':row['raw_reply']}])[-8:]
 save();print(json.dumps({'turn':len(report['turns']),'reply':row['reply'],'preparation_ms':row['metrics']['request_preparation_ms']},ensure_ascii=True),flush=True)
answer=report['turns'][-1]['reply']['reply_text']
report['four_round_memory_correct']='小林' in answer and '绿' in answer and ('十五' in answer or '15' in answer)
for text,expected in [('请原样复述这句话：你好汐蓝今天过得怎么样？','你好汐蓝今天过得怎么样'),
                      ('请把“我今天很开新”改成正确写法。','开心')]:
 row=run(text);row['expected_content_present']=expected in row['reply']['reply_text'];report['extra_tasks'].append(row)
 save();print(json.dumps({'task':text,'reply':row['reply'],'expected':row['expected_content_present']},ensure_ascii=True),flush=True)
report['injected_copy_repair']=run('你好汐蓝今天过得怎么样',inject_copy=True)
repair=report['injected_copy_repair']
report['all_checks_pass']=report['four_round_memory_correct'] and all(t['expected_content_present'] and t['metrics']['quality_retry_count']==0 for t in report['extra_tasks']) and repair['metrics']['quality_retry_count']==1 and not repair['metrics']['possible_question_echo']
save();print(json.dumps({'all_checks_pass':report['all_checks_pass'],'repair':repair},ensure_ascii=True),flush=True)
