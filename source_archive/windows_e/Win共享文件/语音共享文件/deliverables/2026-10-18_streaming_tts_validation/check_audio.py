"""ASR is a word-content screen, never proof of voice identity or naturalness."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid
import wave

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('AURA_TTS_TRIAL_DIR',str(BASE)))
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.transcription import recognize

def normalize(s):return ''.join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',s))
def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a):
        nxt=[i+1]
        for j,y in enumerate(b):nxt.append(min(nxt[-1]+1,row[j+1]+1,row[j]+(x!=y)))
        row=nxt
    return row[-1]

def main():
    import numpy as np
    from scipy.signal import resample_poly
    report=json.loads((HERE/'streaming.json').read_text(encoding='utf-8'))
    checks=[]
    for item in report['cases'][:6]:
        with wave.open(item['wav'],'rb') as audio:
            assert audio.getnchannels()==1 and audio.getsampwidth()==2
            pcm24=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2')
        pcm=resample_poly(pcm24.astype(np.float32),2,3).round().clip(-32768,32767).astype('<i2').tobytes()
        meta={'protocol':'aura-asr-1','board_boot_id':'streaming-tts-validation','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'candidate-asr-screen','generation':1,'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':30000}
        result=recognize({'host':'192.168.50.1','port':8791},meta,pcm,30)
        expected=normalize(item['text']);actual=normalize(result['text'])
        checks.append({'wav':item['wav'],'expected':item['text'],'asr_text':result['text'],'character_error_rate':distance(expected,actual)/max(1,len(expected))})
    value={'status':'COMPLETE_CONTENT_SCREEN_ONLY','voice_similarity':'REQUIRES_LISTENING','cases':checks}
    (HERE/'audio_content.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(value,ensure_ascii=True))

if __name__=='__main__':main()
