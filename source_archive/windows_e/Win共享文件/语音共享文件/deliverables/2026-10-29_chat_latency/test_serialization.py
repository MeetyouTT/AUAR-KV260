"""Reject the formatting hint without changing memory selection or model requests."""
import hashlib,json,sys,types
from pathlib import Path
from unittest.mock import patch
import pytest
from common.conversation_context import build_context,request_cost
from tools import dialogue_stream as ds
H=Path(__file__).resolve().parent
old=types.ModuleType('baseline_dialogue_stream')
exec(compile((H/'before/tools/dialogue_stream.py').read_text(encoding='utf-8'),'r6_stream','exec'),old.__dict__)
@pytest.mark.parametrize('question',['我以前喜欢什么颜色','我的比赛计划是什么','我叫什么名字','请陪我聊聊今天的安排'])
def test_short_and_near_limit_memory_selection_matches_r6(question):
 records=[{'seq':n,'user':('我叫小林，比赛计划是学习画画，喜欢绿色。' if n==1 else '第'+str(n)+'天准备比赛，今天学画画。'),
  'assistant':'我记住了，可以继续聊聊。','status':'played' if n%3 else 'interrupted'} for n in range(1,25)]
 facts=[{'key':'颜色偏好','value':'绿色','source_seq':1,'scope':'conversation'},
        {'key':'称呼','value':'小林','source_seq':1,'scope':'conversation'}]
 candidate=ds.stream_body
 for n in range(0,321,8):
  text=question+'，补充说明'+('学画画'*n)
  with patch.object(ds,'stream_body',old.stream_body):
   try:expected=build_context('fixture',records,text,memories=facts)
   except ValueError:expected=None
  with patch.object(ds,'stream_body',candidate):
   if expected is None:
    with pytest.raises(ValueError):build_context('fixture',records,text,memories=facts)
    continue
   actual=build_context('fixture',records,text,memories=facts)
  assert actual[0]==expected[0]
  for key in ('explicit_fact_sources','source_turns','recent_source_turns','history_messages','context_limit'):
   assert actual[1][key]==expected[1][key]
  assert actual[1]['budget_upper_bound']<=actual[1]['context_limit']==2048
@pytest.mark.parametrize('think,reply_first',[(True,True),(True,False),(False,False),(False,True)])
def test_reasoning_and_legacy_requests_are_byte_semantically_unchanged(think,reply_first):
 args=('fixture',[{'role':'user','content':'公开历史'}],'请解释这个问题')
 assert ds.stream_body(*args,think=think,reply_first=reply_first)==old.stream_body(*args,think=think,reply_first=reply_first)
class Socket:
 def shutdown(self,*a):pass
class Response:
 status=200
 def __init__(self,raw):
  self.rows=[json.dumps({'message':{'content':raw},'done':False},ensure_ascii=False).encode()+b'\n',
             json.dumps({'message':{'content':''},'done':True,'eval_count':20}).encode()+b'\n']
 def readline(self,*a):return self.rows.pop(0) if self.rows else b''
def capture_attempt(history,raw,records):
 class Connection:
  def __init__(self,*a,**kw):self.sock=Socket()
  def connect(self):pass
  def request(self,method,path,body,headers):
   records.append(json.loads(body))
  def getresponse(self):return Response(raw)
  def close(self):pass
 with patch.object(ds.http.client,'HTTPConnection',Connection):
  stream=ds.OllamaReplyStream('http://127.0.0.1:11435','fixture',history,'你好',3,reply_first=True)
  output=list(stream)
 return stream,output
def test_request_fingerprint_tracks_full_sent_body_and_history_without_recording_body():
 raw=json.dumps({'a':'今天辛苦啦，我陪你聊聊。','b':'friendly','c':''},ensure_ascii=False)
 bodies=[];one,_=capture_attempt([],raw,bodies)
 two,_=capture_attempt([{'role':'user','content':'我喜欢画画'}],raw,bodies)
 assert one.metrics['input_sha256']==two.metrics['input_sha256']
 assert one.metrics['request_sha256']!=two.metrics['request_sha256']
 for stream,body in zip((one,two),bodies):
  digest=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  assert stream.metrics['request_sha256']==digest
  assert 'compact_chat_hint' not in stream.metrics
  assert not any(isinstance(v,dict) for v in stream.metrics.values())
def test_format_metric_excludes_spaces_and_escaped_quotes_inside_spoken_text():
 raw=json.dumps({'a':'我们一起读“星 海”吧。里面有一个空格。','b':'friendly','c':''},ensure_ascii=False,indent=2)
 bodies=[];stream,output=capture_attempt([],raw,bodies)
 assert stream.metrics['json_format_whitespace']==13
 assert output[-1][0]=='complete' and output[-1][1]['reply_text']=='我们一起读“星 海”吧。里面有一个空格。'
