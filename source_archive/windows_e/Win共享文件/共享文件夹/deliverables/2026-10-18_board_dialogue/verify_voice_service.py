"""Actual full HTTP service test with historical board audio; no live capture."""
import hashlib
import json
from pathlib import Path
import sys
import time
import wave
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.conversation import ConversationJobs

path=ROOT/'aura/report/recording_20261016/microphone-5s.wav'
with wave.open(str(path),'rb') as wav:pcm=wav.readframes(wav.getnframes())
meta={'protocol':'aura-asr-1','board_boot_id':'historical-board-capture','session_id':'http-service-check',
      'request_id':'actual-service-20261018','generation':1,'capture_id':'historical-20261016',
      'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
config={'enabled':True,'host':'192.168.50.1','port':8792,'timeout_ms':120000}
jobs=ConversationJobs(config,meta['board_boot_id'],HERE/'http_voice_cache')
try:
    started=time.monotonic();reply=jobs.converse(config,meta,pcm,120)
    report={'status':'PASS_ACTUAL_MODELS_OVER_HTTP','historical_audio_only':True,
            'elapsed_seconds':round(time.monotonic()-started,3),'response':reply}
    (HERE/'http_voice_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds'],
                      'transcript':reply['text'],'reply':reply['voice_reply']['reply_text']},ensure_ascii=True))
finally:jobs.close()
