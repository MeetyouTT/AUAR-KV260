"""Actual ASR silence rejection and archived-speech entry; no live microphone."""
import hashlib,json,sys,urllib.request,uuid,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.handsfree_entry import EntryRejected

get=lambda:json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
def meta(pcm):
 return {'protocol':'aura-asr-1','board_boot_id':'entry-probe','session_id':uuid.uuid4().hex,
  'request_id':uuid.uuid4().hex,'capture_id':'archived-probe','generation':1,
  'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
before=get();assert before['handsfree_entry']['version']==1 and not before['busy']
channel=VoiceChannel('192.168.50.1',8792)
report={'actual_models':True,'actual_visual_audio_combination':False,'audio_played':False,
        'new_microphone_recording':False,'playback_ack_sent':False,'live_user_acceptance':False}
try:
 pcm=b'\0\0'*16000
 try:channel.exchange(meta(pcm),pcm,lambda h,p:None,conversation=uuid.uuid4().hex,visual_entry=True)
 except EntryRejected:report['actual_asr_silence_rejected']=True
 else:raise RuntimeError('Silence was accepted as an initial conversation turn')
 after=get()
 assert after['conversation_memory']['turns']==before['conversation_memory']['turns']
 report['silence_no_history_write']=True
 with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as a:
  assert (a.getframerate(),a.getnchannels(),a.getsampwidth())==(16000,1,2)
  pcm=a.readframes(a.getnframes())
 events=[]
 result=channel.exchange(meta(pcm),pcm,lambda h,p:events.append(h),conversation=uuid.uuid4().hex,visual_entry=True)
 report.update(archived_speech_entry_passed=True,
  transcript=next(h['text'] for h in events if h['kind']=='transcript'),reply=result['reply_text'],
  sample_count=result['sample_count'],history_not_playback_committed=not result['playback_verified'])
finally:channel.close()
(HERE/'actual_http.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
