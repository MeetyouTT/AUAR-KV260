"""Actual local PCM -> ASR -> Ollama -> OmniVoice -> Qt device test.

Uses a recorded fixture, not a human microphone capture. Writes actual evidence.
"""
import base64
import json
from pathlib import Path
import time
import urllib.request
import wave
import numpy as np

HERE=Path(__file__).resolve().parent
URL='http://127.0.0.1:8775'
def state():
    with urllib.request.urlopen(URL+'/api/state',timeout=5) as response:return json.load(response)
def command(data):
    request=urllib.request.Request(URL+'/api/command',data=json.dumps(data).encode(),
        headers={'Content-Type':'application/json','Origin':URL})
    with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
def wait_for(predicate,timeout=120):
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        value=state()
        if value.get('error'):raise RuntimeError(value['error'])
        if predicate(value):return value
        time.sleep(.1)
    raise TimeoutError('Dialogue verification timed out')

wait_for(lambda s:s.get('microphone_ready') and s.get('voice_ready'),60)
source=HERE.parent/'2026-10-11_omnivoice_liveness/runs/qwen/greeting.wav'
with wave.open(str(source)) as wav:
    samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')
    rate=wav.getframerate()
pcm=np.interp(np.arange(int(len(samples)*16000/rate))*rate/16000,np.arange(len(samples)),samples).astype('<i2')
started=time.monotonic();command({'type':'microphone','pcm':base64.b64encode(pcm.tobytes()).decode()})
first=wait_for(lambda s:s.get('phase')=='SPEAKING' and s.get('playing'))
first_latency=time.monotonic()-started
assert '你好' in first['dialogue_input']
print('PCM_CHAIN_PLAYING',round(first_latency,3),first['reply'],flush=True)
wait_for(lambda s:s.get('phase')=='IDLE' and not s.get('playing'),30)
started=time.monotonic();command({'type':'dialogue','text':'你刚才听到我说了什么？'})
second=wait_for(lambda s:s.get('phase')=='SPEAKING' and s.get('playing'))
second_latency=time.monotonic()-started
print('FOLLOWUP_PLAYING',round(second_latency,3),second['reply'],flush=True)
command({'type':'event','event':'cancel'})
cancelled=wait_for(lambda s:s.get('phase')=='IDLE' and not s.get('playing'),3)
evidence=command({'type':'save_evidence'})
report=dict(status='PASS',scope='recorded PCM fixture through actual ASR, real Ollama, OmniVoice16 and Qt audio; physical microphone capture remains for user',
            fixture=str(source.relative_to(HERE.parent)),first_submission_to_play_seconds=first_latency,
            second_submission_to_play_seconds=second_latency,first=first,second=second,
            cancelled=cancelled,evidence=evidence)
(HERE/'chain_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHAIN_PASS; evidence saved',flush=True)
