"""Actual archived audio -> ASR/27B/TTS over durable HTTP, no playback ACK."""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import sys
import uuid
import wave

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.conversation_store import ConversationStore

parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['before_restart','after_restart'],required=True)
args=parser.parse_args()
selection=HERE/'http_probe_selection.json'
if args.phase=='before_restart':
    if selection.exists():raise SystemExit('Retain existing evidence; do not overwrite probe')
    cid=uuid.uuid4().hex;selection.write_text(json.dumps({'conversation_id':cid}),encoding='utf-8')
else:cid=json.loads(selection.read_text())['conversation_id']
with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as audio:
    assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
    pcm=audio.readframes(audio.getnframes())
meta={'protocol':'aura-asr-1','board_boot_id':'http-probe-'+uuid.uuid4().hex,
      'session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'archived-audio-probe',
      'generation':1,'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
events=[]
channel=VoiceChannel('192.168.50.1',8792,feedback=True)
try:result=channel.exchange(meta,pcm,lambda h,p:events.append(h),conversation=cid)
finally:channel.close()
end=next(row for row in events if row['kind']=='end')
report={'phase':args.phase,'actual_models':True,'new_microphone_recording':False,'audio_played':False,
        'playback_ack_sent':False,'context':end['timing']['conversation_context'],
        'transcript':next(row['text'] for row in events if row['kind']=='transcript'),
        'reply':result['reply_text'],'samples':result['sample_count'],'sha256':result['pcm_sha256']}
assert report['context']['archive_turns']==(0 if args.phase=='before_restart' else 1)
store=ConversationStore(ROOT/'deliverables/2026-10-18_board_dialogue/model_host/conversations.sqlite3')
records=store.records(cid)
assert len(records)==(1 if args.phase=='before_restart' else 2)
assert all(row['status']=='generated' for row in records)
report['unplayed_assistant_not_committed']=True
(HERE/('http_'+args.phase+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
