"""Actual model check using a previously captured MCP01 WAV, not a new board recording."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import wave

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.asr_wire import encode_context, response
from tools import dialogue_host_ollama as dialogue
from tools.selected_voice_service import VoiceWorker

def main():
    fixture=ROOT/'aura/report/recording_20261016/microphone-5s.wav'
    with wave.open(str(fixture),'rb') as audio:
        assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
        count=audio.getnframes();pcm=audio.readframes(count)
    meta={'protocol':'aura-asr-1','board_boot_id':'historical-board-capture','session_id':'host-verification',
          'request_id':'mcp01-20261018','generation':1,'capture_id':'historical-20261016',
          'sample_count':count,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':30000}
    connection=http.client.HTTPConnection('192.168.50.1',8791,timeout=30)
    try:
        connection.request('GET','/health')
        health=connection.getresponse();assert health.status==200
        health=json.loads(health.read())
    finally:connection.close()
    connection=http.client.HTTPConnection('192.168.50.1',8791,timeout=30)
    started=time.perf_counter()
    try:
        connection.request('POST','/v1/asr/transcribe',body=pcm,
                           headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta)})
        answer=connection.getresponse();raw=answer.read()
        if answer.status!=200:raise RuntimeError(raw.decode())
        recognized=response(json.loads(raw),meta)
    finally:connection.close()
    asr_seconds=time.perf_counter()-started
    request={'request_id':'host-voice-check','transcript':recognized['text'],'scene_state':{'scene_seq':1},
             'allowed_emotions':['neutral','friendly','happy','sad'],'allowed_avatar_actions':[]}
    started=time.perf_counter()
    reply=dialogue.build_response(request,'ollama','qwen3:4b-instruct-2507-q4_K_M',strict=True,fast=True)
    llm_seconds=time.perf_counter()-started
    llm_timings=dict(dialogue.LAST_TIMINGS)
    voice=VoiceWorker(HERE/'host_voice',python=sys.executable,
                      model_path=ROOT/'aura/models/tts/OmniVoice',engine='omnivoice')
    try:
        voice.warmup()
        if not voice.ready:raise RuntimeError(voice.error)
        generated=voice.generate(reply['reply_text'])
    finally:voice.close()
    report={'status':'PASS_HOST_ACTUAL_MODELS','scope':'Historical board WAV -> host ASR -> actual Qwen3 -> OmniVoice16 WAV',
            'new_board_capture_verified':False,'board_playback_verified':False,'asr_health':health,
            'input_wav':str(fixture.relative_to(ROOT)),'input_pcm_sha256':meta['pcm_sha256'],
            'transcription':recognized,'asr_http_seconds':round(asr_seconds,3),
            'dialogue':reply,'llm_seconds':round(llm_seconds,3),'llm_timings':llm_timings,'voice':generated}
    (HERE/'host_chain_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'transcript':recognized['text'],'reply':reply['reply_text'],
                      'asr_seconds':report['asr_http_seconds'],'llm_seconds':report['llm_seconds'],
                      'wav':generated['path']},ensure_ascii=True),flush=True)

if __name__=='__main__':main()
