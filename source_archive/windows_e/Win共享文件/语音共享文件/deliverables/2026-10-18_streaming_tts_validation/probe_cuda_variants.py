"""Diagnose CUDA attention/cache correctness before any latency claim."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import uuid
import wave
from probe_streaming import request,TEXTS
from check_audio import distance,normalize

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('AURA_TTS_TRIAL_DIR',str(BASE)))
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.transcription import recognize

def post(path,body):
    c=http.client.HTTPConnection('127.0.0.1',51889,timeout=120)
    try:
        c.request('POST',path,body=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        r=c.getresponse();data=r.read()
        if r.status!=200:raise RuntimeError((r.status,data[:1000]))
        return json.loads(data) if data else {}
    finally:c.close()

def transcribe(path):
    import numpy as np
    from scipy.signal import resample_poly
    with wave.open(str(path),'rb') as a: samples=np.frombuffer(a.readframes(a.getnframes()),dtype='<i2')
    pcm=resample_poly(samples.astype(np.float32),2,3).round().clip(-32768,32767).astype('<i2').tobytes()
    meta={'protocol':'aura-asr-1','board_boot_id':'cuda-cache-diagnosis','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'cuda-diagnosis','generation':1,'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':30000}
    return recognize({'host':'192.168.50.1','port':8791},meta,pcm,30)['text']

def main():
    report={'status':'RUNNING','cases':[]}
    for mode,fa in (('f16_cache_no_flash',False),('f16_cache_flash',True)):
        post('/model/unload',{})
        loaded=post('/model/load',{'model':'D:/AIModels/cosyvoice3-streaming-validation/CosyVoice3-2512_Q8_0.gguf','backend':'CUDA0','n_threads':4,'max_llm_len':1024,'inference_buffer_policy':'balanced','llm_kv_cache_type':'f16','dit_kv_cache_type':'f16','dit_kv_fixed_slots':1,'dit_kv_cache_length':4096,'llm_use_flash_attn':fa,'flow_use_flash_attn':fa})
        c=http.client.HTTPConnection('127.0.0.1',51889,timeout=5)
        c.request('GET','/status');r=c.getresponse();status=json.loads(r.read());c.close()
        assert status['k_cache_type']=='f16' and status['v_cache_type']=='f16' and status['llm_use_flash_attn']==fa and status['flow_use_flash_attn']==fa, status
        loaded['verified_status']=status
        # Runtime model reload may clear speakers; restore the exact prompt.
        c=http.client.HTTPConnection('127.0.0.1',51889,timeout=5)
        c.request('GET','/speaker');r=c.getresponse();speakers=json.loads(r.read());c.close()
        if 'xilan' not in speakers:post('/speaker',{'type':'gguf','name':'xilan','path':'D:/AIModels/cosyvoice3-streaming-validation/xilan-reference.gguf'})
        for i,text in enumerate(TEXTS):
            row=request(text,chunk_tokens=25,name=f'{mode}-{i}')
            row['mode']=mode;row['model_load']=loaded
            row['asr_text']=transcribe(row['wav'])
            row['character_error_rate']=distance(normalize(text),normalize(row['asr_text']))/len(normalize(text))
            report['cases'].append(row)
            (HERE/'variants.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:row[k] for k in ('mode','first_pcm_ms','total_ms','asr_text','character_error_rate')},ensure_ascii=True),flush=True)
    report['status']='COMPLETE_NOT_DEPLOYED'
    report['passed_content']=[mode for mode in {r['mode'] for r in report['cases']} if all(r['character_error_rate']<=.15 for r in report['cases'] if r['mode']==mode)]
    (HERE/'variants.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if report['passed_content']:
        chosen=min(report['passed_content'],key=lambda mode:sum(r['total_ms'] for r in report['cases'] if r['mode']==mode))
        fa=chosen=='f16_cache_flash'
        post('/model/unload',{})
        post('/model/load',{'model':'D:/AIModels/cosyvoice3-streaming-validation/CosyVoice3-2512_Q8_0.gguf','backend':'CUDA0','n_threads':4,'max_llm_len':1024,'inference_buffer_policy':'balanced','llm_kv_cache_type':'f16','dit_kv_cache_type':'f16','dit_kv_fixed_slots':1,'dit_kv_cache_length':4096,'llm_use_flash_attn':fa,'flow_use_flash_attn':fa})
        post('/speaker',{'type':'gguf','name':'xilan','path':'D:/AIModels/cosyvoice3-streaming-validation/xilan-reference.gguf'})
        report['expanded_configuration']=chosen
        (HERE/'variants.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        for script in ('probe_streaming.py','check_audio.py','probe_pipeline.py'):
            subprocess.run([sys.executable,'-B','-u',str(BASE/script)],check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
            if script=='check_audio.py' and any(r['character_error_rate']>.15 for r in json.loads((HERE/'audio_content.json').read_text(encoding='utf-8'))['cases']):break

if __name__=='__main__':main()
