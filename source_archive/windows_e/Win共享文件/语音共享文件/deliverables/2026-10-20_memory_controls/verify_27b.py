"""Actual existing 27B with synthetic scoped facts; no TTS or board playback."""
import json, sys, time, urllib.request, uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.conversation_store import ConversationStore
from common.conversation_context import build_context
from tools.dialogue_stream import OllamaReplyStream
from tools.board_model_host import MODEL, OLLAMA_HOST
from tests.framework.test_voice_channel import owner

run=HERE/('text_probe_'+uuid.uuid4().hex[:10]);run.mkdir()
store=ConversationStore(run/'synthetic.sqlite3');cid=uuid.uuid4().hex
steps=[('记住：项目=海风',None,None),
 ('我的项目叫什么？',['海风'],[]),
 ('更正记忆：项目=晨光',None,None),
 ('我的项目叫什么？',['晨光'],['海风']),
 ('忘记我的项目',None,None),
 ('我的项目叫什么？没有资料就说不知道，不要猜。',[],['海风','晨光']),
 ('记住：称呼=小林',None,None),
 ('记住：颜色偏好=绿色',None,None),
 ('我最喜欢什么颜色？',['绿色'],[]),
 ('清空本次对话记忆',None,None),
 ('我叫什么名字、喜欢什么颜色？没有资料就说不知道，不要猜。',[],['小林','绿色'])]
rows=[]
for n,(text,required,forbidden) in enumerate(steps,1):
 health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
 if health['busy']:raise RuntimeError('Foreground busy; stopped without further inference')
 meta=owner('memory-text-%d'%n,n);store.begin(cid,meta,text,text)
 reply=store.memory_command(meta,text);history=[];metrics={};model_metrics={};started=time.monotonic()
 if reply is None:
  records,facts=store.context_snapshot(cid,exclude=meta['request_id'])
  history,metrics=build_context(MODEL,records,text,memories=facts)
  stream=OllamaReplyStream(OLLAMA_HOST,MODEL,history,text,90,reply_first=True)
  try:
   for kind,value in stream:
    if kind=='complete':reply=value['reply_text']
  finally:stream.cancel()
  model_metrics=stream.metrics
  if reply is None:raise RuntimeError('Actual model did not complete')
  assert all(word in reply for word in required),(n,reply,required)
  assert all(word not in reply for word in forbidden),(n,reply,forbidden)
  if n in (6,11):assert not history,(n,'Forgotten transcript still in prompt')
 store.generated(meta,reply,480,'0'*64);store.played(meta,480,'0'*64) # simulation only
 rows.append({'step':n,'input':text,'reply':reply,'model_called':required is not None,
  'context':metrics,'model_metrics':model_metrics,'seconds':round(time.monotonic()-started,2),'passed':True})
 (run/'turns.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'step':n,'passed':True,'model_called':required is not None,'reply':reply},ensure_ascii=True),flush=True)
 store=ConversationStore(run/'synthetic.sqlite3')
summary={'passed':True,'steps':len(rows),'actual_model_questions':sum(r['model_called'] for r in rows),
 'model':MODEL,'database_reopened_each_step':True,'playback_ack':'simulation_no_audio',
 'production_conversation_database_modified':False,'board_microphone_or_playback':False,'evidence':str(run)}
(HERE/'actual_27b_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary),flush=True)
