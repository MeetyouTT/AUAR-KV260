"""Real ASR/27B/TTS, separate synthetic CID, active recall and stale ACK checks.

Command insertion uses the same store API in a separate connection, not live
speech. It does not certify recognition of a human spoken memory command.
"""
import hashlib, http.client, json, sys, uuid, wave
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.conversation_store import ConversationStore
from common.conversation_context import build_context
from tools.board_model_host import MODEL
from tests.framework.test_voice_channel import owner

run=HERE/('http_probe_'+uuid.uuid4().hex[:10]);run.mkdir()
cid=uuid.uuid4().hex
store=ConversationStore(ROOT/'deliverables/2026-10-18_board_dialogue/model_host/conversations.sqlite3')
def command(n,text):
 meta=owner('synthetic-memory-'+uuid.uuid4().hex,n)
 store.begin(cid,meta,text,text)
 return store.memory_command(meta,text)
command(1,'记住：项目=测试星舟七')
with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as audio:
 assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
 pcm=audio.readframes(audio.getnframes())
rows=[]
for n in (1,2):
 meta={'protocol':'aura-asr-1','board_boot_id':'memory-http-'+uuid.uuid4().hex,
  'session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'archived-audio-probe',
  'generation':1,'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
 channel=VoiceChannel('192.168.50.1',8792,feedback=True);events=[]
 try:result=channel.exchange(meta,pcm,lambda h,p:events.append(h),conversation=cid)
 finally:channel.close()
 end=next(h for h in events if h['kind']=='end');context=end['timing']['conversation_context']
 assert context['explicit_facts']==(1 if n==1 else 0),context
 row={'step':n,'actual_asr_llm_tts':True,'explicit_facts_in_actual_host_context':context['explicit_facts'],
  'transcript_characters':len(next(h['text'] for h in events if h['kind']=='transcript')),
  'reply_characters':len(result['reply_text']),'output_samples':result['sample_count'],
  'output_pcm_sha256':result['pcm_sha256'],'spoken_command_recognition_verified':False}
 if n==1:
  command(2,'忘记我的项目')
  connection=http.client.HTTPConnection('192.168.50.1',8792,timeout=4)
  try:
   body=json.dumps({'context':meta,'voice_sample_count':result['sample_count'],'pcm_sha256':result['pcm_sha256']})
   connection.request('POST','/v1/voice/channel/played',body,{'Content-Type':'application/json'})
   response=connection.getresponse();response.read();assert response.status==400,response.status
   row['stale_ack_rejected_after_forget']=True
  finally:connection.close()
  history,_=build_context(MODEL,store.records(cid),'项目叫什么',memories=store.facts(cid))
  assert '测试星舟七' not in json.dumps(history,ensure_ascii=False)
 rows.append(row);print(json.dumps(row),flush=True)
command(3,'清空本次对话记忆')
report={'passed':True,'cases':rows,'production_database_scope':'new isolated synthetic conversation only',
 'test_conversation_recall_cleared':True,'existing_user_conversations_modified':False,
 'microphone_opened':False,'audio_played':False,'ordinary_playback_ack_committed':False,
 'human_memory_voice_verified':False,'evidence':str(run)}
(run/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(HERE/'http_summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'evidence':str(run)}),flush=True)
