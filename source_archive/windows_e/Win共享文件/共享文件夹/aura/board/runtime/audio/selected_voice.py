"""Reusable host-side selected voice: one Base ICL prompt and verified WAV cache.

Synthesis is local to the PC. Playback/FSM/device adapters consume the returned
WAV rather than importing a GPU model on the board or UI thread.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import threading
import time
import unicodedata
import wave

AURA=Path(__file__).resolve().parents[3]
VOICE=AURA.parent/'deliverables'/'2026-10-06_voice_selected_soft_young'
WORKSPACE=AURA.parent.parent


def normalize_text(text):
    if not isinstance(text,str):raise ValueError('Text must be a string')
    text=re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip()
    if not text or len(text)>240:raise ValueError('Enter 1 to 240 characters')
    if any(ord(c)<32 for c in text):raise ValueError('Control characters are not supported')
    return text


class SelectedVoiceSynthesizer:
    normalize_text=staticmethod(normalize_text)
    def __init__(self,cache_root,model_path=None,voice_root=VOICE):
        self.cache_root=Path(cache_root);self.cache_root.mkdir(parents=True,exist_ok=True)
        self.voice_root=Path(voice_root);self.model_path=Path(model_path or WORKSPACE/'tmp/Qwen3-TTS-12Hz-1.7B-Base')
        self.selection=json.loads((self.voice_root/'selection.json').read_text(encoding='utf-8'))
        self.reference=self.voice_root/self.selection['reference_audio']
        if hashlib.sha256(self.reference.read_bytes()).hexdigest()!=self.selection['reference_sha256']:
            raise ValueError('Selected voice reference changed')
        self.revision=json.loads((self.voice_root/'base_model_verification.json').read_text(encoding='utf-8'))['revision']
        self.model=None;self.prompt=None;self.lock=threading.Lock()

    def identity(self,text):
        value={'version':2,'text':self.normalize_text(text),'model_revision':self.revision,
               'reference_sha256':self.selection['reference_sha256'],'reference_text':self.selection['reference_text'],
               'language':'Chinese','seed':8701,'max_new_tokens':1200,'active_rms_target':.1,'peak_limit':.95}
        key=hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
        return key,value

    def cached(self,text):
        key,identity=self.identity(text);path=self.cache_root/f'{key}.wav';record=self.cache_root/f'{key}.json'
        if not path.is_file() or not record.is_file():return None
        try:
            data=json.loads(record.read_text(encoding='utf-8'))
            if data['identity']!=identity or hashlib.sha256(path.read_bytes()).hexdigest()!=data['sha256']:return None
            with wave.open(str(path),'rb') as audio:
                if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(24000,1,2):return None
            return dict(data,cache_hit=True,path=str(path))
        except (OSError,ValueError,KeyError,wave.Error):return None

    def load(self):
        if self.model is not None:return
        import torch
        from qwen_tts import Qwen3TTSModel
        if not torch.cuda.is_available():raise RuntimeError('Selected voice requires the configured PC CUDA runtime')
        torch.set_num_threads(4)
        self.model=Qwen3TTSModel.from_pretrained(str(self.model_path),device_map='cuda:0',dtype=torch.bfloat16,
                   attn_implementation='sdpa',local_files_only=True)
        self.prompt=self.model.create_voice_clone_prompt(ref_audio=str(self.reference),
                      ref_text=self.selection['reference_text'],x_vector_only_mode=False)

    def synthesize(self,text):
        text=self.normalize_text(text)
        with self.lock:
            cached=self.cached(text)
            if cached:return cached
            import numpy as np
            import soundfile as sf
            import torch
            key,identity=self.identity(text);started=time.perf_counter();self.load();torch.manual_seed(8701)
            with torch.inference_mode():
                waves,rate=self.generate_waves(text)
            samples=np.asarray(waves[0],dtype=np.float32)
            if int(rate)!=24000 or samples.ndim!=1 or not len(samples) or not np.isfinite(samples).all():raise ValueError('Invalid synthesized audio')
            # Near-active RMS normalization, preserving pauses and voice speed.
            n=480;rms=np.array([np.sqrt(np.mean(samples[i:i+n]**2)) for i in range(0,len(samples),n)])
            active=rms[rms>max(.005,float(rms.max())*.03)]
            if not len(active):raise ValueError('Silent generated audio')
            gain=min(.1/float(np.sqrt(np.mean(active**2))),.95/max(float(np.abs(samples).max()),1e-6))
            path=self.cache_root/f'{key}.wav';temporary=self.cache_root/f'{key}.part.wav'
            sf.write(temporary,samples*gain,rate,subtype='PCM_16');temporary.replace(path)
            data={'status':'COMPLETE','key':key,'identity':identity,'voice':'柔亮俏皮',
                  'duration_seconds':len(samples)/rate,'sample_rate':24000,'channels':1,
                  'generation_seconds':time.perf_counter()-started,'normalization_gain':gain,
                  'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cache_hit':False,'path':str(path),
                  'scope':'PC local non-streaming synthesis; not board inference'}
            record=self.cache_root/f'{key}.json';temp_record=self.cache_root/f'{key}.part.json'
            temp_record.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp_record.replace(record)
            return data

    def generate_waves(self,text):
        return self.model.generate_voice_clone(text=text,language='Chinese',voice_clone_prompt=self.prompt,
                                              non_streaming_mode=True,max_new_tokens=1200)


def worker_main(cache_root,model_path=None):
    import sys
    try:sys.stdout.reconfigure(encoding='utf-8');sys.stdin.reconfigure(encoding='utf-8')
    except AttributeError:pass
    synth=SelectedVoiceSynthesizer(cache_root,model_path)
    for line in sys.stdin:
        try:
            request=json.loads(line);result=synth.synthesize(request['text'])
            print('RESULT '+json.dumps({'ok':True,'result':result},ensure_ascii=False),flush=True)
        except Exception as exc:
            print('RESULT '+json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cache-root',required=True,type=Path)
    parser.add_argument('--model-path',type=Path);args=parser.parse_args();worker_main(args.cache_root,args.model_path)
