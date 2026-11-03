"""Test the deployed board client with historical PCM; no recording or playback."""
import base64
import json
import wave
from pathlib import Path
from board_ssh import ssh,HERE

ROOT=HERE.parents[1]
with wave.open(str(ROOT/'aura/report/recording_20261016/microphone-5s.wav'),'rb') as audio:
    pcm=audio.readframes(audio.getnframes())
script=r'''
import base64,hashlib,json,sys,time
from pathlib import Path
runtime=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
sys.path.insert(0,str(runtime/'aura'))
from board.runtime.audio.conversation import ConversationJobs
from tools.selected_voice_service import SpeechJobs,VoiceWorker
pcm=base64.b64decode(PCM)
meta={'protocol':'aura-asr-1','board_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
      'session_id':'historical-board-client-probe','request_id':'client-probe-20261018','generation':1,
      'capture_id':'historical-recording','sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
config={'enabled':True,'host':'192.168.50.1','port':8792,'timeout_ms':120000}
root=Path('/home/root/aura-voice-dialogue-20261018/client-probe')
jobs=ConversationJobs(config,meta['board_boot_id'],root/'cache')
speech=SpeechJobs(root,VoiceWorker(root,cached_only=True))
try:
    start=time.monotonic();answer=jobs.converse(config,meta,pcm,120)
    imported=speech.import_generated(answer['voice_reply'])
    print(json.dumps({'status':'PASS_BOARD_CLIENT_ACTUAL_MODELS','historical_recording':True,
                      'physical_playback':False,'elapsed_seconds':round(time.monotonic()-start,3),
                      'transcript':answer['text'],'voice_reply':answer['voice_reply'],'imported_job':imported}))
finally:jobs.close();speech.close()
'''.replace('PCM',repr(base64.b64encode(pcm).decode()))
answer=ssh('python3 -',script,timeout=135)
(HERE/'board_client_probe.json').write_text(answer,encoding='utf-8')
report=json.loads(answer)
print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],
                  'reply':report['voice_reply']['reply_text']},ensure_ascii=True))
