"""Direct local ASR; no HTTP service, audio transmission, playback or chat."""
import json
from pathlib import Path
import socket
import sys
import time
import wave

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
def blocked(*args,**kwargs):raise RuntimeError('Network forbidden during local ASR diagnosis')
socket.socket.connect=blocked
from tools.asr_server import Paraformer
engine=Paraformer(ROOT/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14')
config=json.loads((HERE/'actual_experiment.json').read_text(encoding='utf-8'))
sid=config['session_id'];rows=[]
for index in (1,2,3,4):
    with wave.open(str(ROOT/'声纹测试录音'/sid/('clip-%02d.wav'%index))) as audio:
        pcm=audio.readframes(audio.getnframes())
    started=time.perf_counter();text=engine.transcribe(pcm)
    rows.append({'clip':index,'text':text,'recognition_ms':round((time.perf_counter()-started)*1000,2)})
result={'scope':'DIRECT_LOCAL_ASR_DIAGNOSTIC_NOT_SPEAKER_GROUND_TRUTH','network_blocked':True,'clips':rows}
(HERE/'actual_capture_asr_local.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
