"""ASR-only check of four explicitly collected test clips; no chat/history."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import wave

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.asr_wire import encode_context,response as validate_response
config=json.loads((HERE/'actual_experiment.json').read_text(encoding='utf-8'))
sid=config['session_id']; rows=[]
for index in (1,2,3,4):
    with wave.open(str(ROOT/'声纹测试录音'/sid/('clip-%02d.wav'%index))) as audio:
        pcm=audio.readframes(audio.getnframes())
    meta={'protocol':'aura-asr-1','board_boot_id':'speaker-explicit-test','session_id':sid,
          'request_id':'speaker-clip-'+str(index),'generation':index,'capture_id':sid+'-'+str(index),
          'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':30000}
    connection=http.client.HTTPConnection('192.168.50.1',8791,timeout=35)
    try:
        connection.request('POST','/v1/asr/transcribe',pcm,{'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta)})
        reply=connection.getresponse();value=json.loads(reply.read())
        if reply.status!=200:raise ValueError(value)
        value=validate_response(value,meta)
        rows.append({'clip':index,'text':value['text'],'recognition_ms':value['recognition_ms'],
                     'model_id':value['model_id']})
    finally:connection.close()
(HERE/'actual_capture_asr.json').write_text(json.dumps({'scope':'ASR_DIAGNOSTIC_ONLY_NOT_SPEAKER_GROUND_TRUTH','clips':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
