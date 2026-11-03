"""Actual Paraformer HTTP + recorder-controller test using recorded WAV bytes."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request
import wave

AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(AURA))
from board.runtime.audio.capture import CapturedAudio,FORMAT
from board.runtime.audio.transcription import TranscriptionJobs,DEFAULTS
from host.model_service.protocol import AudioRef
from tools.board_recording import RecordingController
from tests.framework.test_board_recording import Controller,Capture

WORK=Path(__file__).resolve().parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8791/health',timeout=3) as r:health=json.load(r)
assert health['ready'] and health['source_kind']=='actual'
records=[]
for name,path in [('official_probe',AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'),
                  ('board_mcp01_5s',AURA/'report/recording_20261016/microphone-5s.wav')]:
    raw=path.read_bytes()
    with wave.open(str(path),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,16000)
        pcm=w.readframes(w.getnframes())
    class RecordedWav(Capture):
        def take(self):
            self.state='IDLE'
            return CapturedAudio(name,AudioRef(1,0,len(pcm)//2,FORMAT),pcm,100,100+len(pcm)//32)
        def snapshot(self):return {'state':self.state,'sample_count':len(pcm)//2,'error':''}
    jobs=TranscriptionJobs(dict(DEFAULTS,enabled=True),'host-replay-test')
    owner=RecordingController(Controller(),capture_factory=RecordedWav,transcriber=jobs)
    try:
        started=time.monotonic();owner.record_start();owner.record_stop()
        while time.monotonic()-started<35:
            public=owner.public();result=public['local_transcription']
            if result['state'] in ('READY','EMPTY','ERROR'):break
            time.sleep(.02)
        assert result['state']=='READY',result
        assert result['model_id']==health['model_id']
        if name=='official_probe':assert result['text']==health['probe_text']
        record={'input':str(path),'wav_sha256':hashlib.sha256(raw).hexdigest(),
                'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'sample_count':len(pcm)//2,
                'result':result,'wall_seconds':round(time.monotonic()-started,3)}
        records.append(record)
    finally:owner.close()
report={'status':'PASS','scope':'HOST_ACTUAL_MODEL_HTTP_AND_CONTROLLER',
        'live_board_gui_or_lan_test':False,'human_reference_transcript_available':False,
        'health':health,'records':records}
(WORK/'actual_asr.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
