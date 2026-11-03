"""Host-only OmniVoice 16-step voice, isolated cache and exact selected reference."""
import hashlib
import io
import json
from pathlib import Path
import random
import re
import sys
import threading
import time
import unicodedata

AURA=Path(__file__).resolve().parents[3]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer,VOICE

REVISION='c5fdb5ccb189668d56333f77ba2629f4cd7535f4'
PARAMETERS=dict(num_step=16,speed=1.0,guidance_scale=2.0,denoise=True,
                preprocess_prompt=True,postprocess_output=True)

def normalize_omnivoice_text(text):
    if not isinstance(text,str):raise ValueError('Text must be a string')
    text=re.sub(r'\s+',' ',unicodedata.normalize('NFC',text)).strip()
    if not text or len(text)>240:raise ValueError('Enter 1 to 240 characters')
    if any(ord(c)<32 for c in text):raise ValueError('Control characters are not supported')
    return text

class OmniVoiceSynthesizer(SelectedVoiceSynthesizer):
    normalize_text=staticmethod(normalize_omnivoice_text)

    def __init__(self,cache_root,model_path,voice_root=VOICE,*,memory_only=False):
        if not model_path:raise ValueError('Configure the local OmniVoice model directory')
        self.memory_only=bool(memory_only)
        if self.memory_only:
            # Do not invoke the disk-cache constructor, even with a temporary
            # directory. Reference/model files are read-only model resources.
            self.cache_root=None;self.voice_root=Path(voice_root);self.model_path=Path(model_path)
            self.selection=json.loads((self.voice_root/'selection.json').read_text(encoding='utf-8'))
            self.reference=self.voice_root/self.selection['reference_audio']
            if hashlib.sha256(self.reference.read_bytes()).hexdigest()!=self.selection['reference_sha256']:
                raise ValueError('Selected voice reference changed')
            self.model=None;self.prompt=None;self.lock=threading.Lock()
        else:super().__init__(cache_root,model_path,voice_root)
        self.revision=REVISION
        manifest=json.loads((self.model_path/'download_identity.json').read_text(encoding='utf-8'))
        if manifest.get('repository')!='k2-fsa/OmniVoice' or manifest.get('revision')!=REVISION:
            raise ValueError('OmniVoice model revision differs from verified audition')
        for entry in manifest['files']:
            if (self.model_path/entry['path']).stat().st_size!=entry['bytes']:
                raise ValueError('Incomplete OmniVoice model: '+entry['path'])

    def identity(self,text):
        value=dict(version=1,engine='omnivoice',text=self.normalize_text(text),model_revision=self.revision,
                   reference_sha256=self.selection['reference_sha256'],reference_text=self.selection['reference_text'],
                   seed=8701,parameters=PARAMETERS,attention='sdpa',dtype='float16',
                   active_rms_target=.1,peak_limit=.95)
        key=hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
        return key,value

    def load(self):
        if self.model is not None:return
        import torch
        from omnivoice import OmniVoice
        if not torch.cuda.is_available():raise RuntimeError('OmniVoice requires PC CUDA runtime')
        torch.set_num_threads(4)
        self.model=OmniVoice.from_pretrained(str(self.model_path),device_map='cuda:0',dtype=torch.float16,
                                            attn_implementation='sdpa',local_files_only=True)
        self.prompt=self.model.create_voice_clone_prompt(ref_audio=str(self.reference),ref_text=self.selection['reference_text'])

    def generate_waves(self,text):
        import numpy as np
        random.seed(8701);np.random.seed(8701)
        return self.model.generate(text=text,voice_clone_prompt=self.prompt,**PARAMETERS),int(self.model.sampling_rate)

    def synthesize(self,text):
        if self.memory_only:raise RuntimeError('Memory-only worker cannot write the voice cache')
        return super().synthesize(text)

    def synthesize_pcm(self,text):
        """Uncached RAM PCM with the same seed, voice and gain as WAV mode."""
        from common.model_inference_wire import MAX_PCM,audio_payload
        import numpy as np
        import soundfile as sf
        import torch
        text=self.normalize_text(text)
        with self.lock:
            self.load();torch.manual_seed(8701)
            with torch.inference_mode():waves,rate=self.generate_waves(text)
            samples=np.asarray(waves[0],dtype=np.float32)
            if (int(rate)!=24000 or samples.ndim!=1 or not 0<len(samples)<=MAX_PCM//2
                    or not np.isfinite(samples).all()):raise ValueError('Invalid synthesized audio')
            n=480;rms=np.array([np.sqrt(np.mean(samples[i:i+n]**2)) for i in range(0,len(samples),n)])
            active=rms[rms>max(.005,float(rms.max())*.03)]
            if not len(active):raise ValueError('Silent generated audio')
            gain=min(.1/float(np.sqrt(np.mean(active**2))),.95/max(float(np.abs(samples).max()),1e-6))
            output=io.BytesIO()
            sf.write(output,samples*gain,rate,subtype='PCM_16',format='RAW',endian='LITTLE')
            return {'audio':audio_payload(output.getvalue(),int(rate)),'cache_hit':False}

def release_idle_cuda_cache():
    """Drop unused allocator blocks after inference, never tensors or weights."""
    import torch
    if not torch.cuda.is_initialized():return {'available':False}
    try:
        allocated=int(torch.cuda.memory_allocated())
        before=int(torch.cuda.memory_reserved())
        started=time.perf_counter()
        if before-allocated>=64*1024*1024:torch.cuda.empty_cache()
        after=int(torch.cuda.memory_reserved())
        return {'available':True,'allocated_bytes':allocated,
                'reserved_before_bytes':before,'reserved_after_bytes':after,
                'released_bytes':max(0,before-after),
                'trim_ms':round((time.perf_counter()-started)*1000,2)}
    except RuntimeError as exc:
        # This optional housekeeping must not replace a valid completed WAV.
        # Genuine inference/worker failures retain the existing fault path.
        return {'available':False,'error':type(exc).__name__}

def worker_main(cache_root,model_path,*,memory_only=False):
    sys.stdout.reconfigure(encoding='utf-8');sys.stdin.reconfigure(encoding='utf-8')
    synth=OmniVoiceSynthesizer(cache_root,model_path,memory_only=memory_only)
    for line in sys.stdin:
        request_id=None
        try:
            request=json.loads(line)
            request_id=request.get('request_id')
            import torch
            from tools.cuda_memory_stats import begin as begin_memory,finish as finish_memory
            before_memory=begin_memory(torch)
            if request.get('type')=='warmup':
                import torch
                synth.load();torch.manual_seed(8701)
                # Always run inference: a cached short clip cannot warm CUDA kernels.
                with torch.inference_mode():synth.generate_waves('嗯，我在呢。')
                torch.cuda.synchronize();result={'ready':True}
            else:result=synth.synthesize_pcm(request['text']) if memory_only else synth.synthesize(request['text'])
            result=dict(result,cuda_inference=finish_memory(torch,before_memory,
                cache_hit=bool(result.get('cache_hit')),warmup=request.get('type')=='warmup'))
            result=dict(result,cuda_idle_cache=release_idle_cuda_cache())
            print('RESULT '+json.dumps({'ok':True,'request_id':request_id,'result':result},ensure_ascii=False),flush=True)
        except Exception as exc:
            # RAM inference must never leak request text through exception text.
            error=type(exc).__name__ if memory_only else str(exc)
            print('RESULT '+json.dumps({'ok':False,'request_id':request_id,'error':error},ensure_ascii=False),flush=True)
        finally:
            if memory_only:
                # A long-lived idle worker must not retain the last request
                # line/text or generated PCM while waiting on stdin.
                request=None;result=None;line=None;request_id=None

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--cache-root',type=Path)
    parser.add_argument('--memory-only',action='store_true')
    parser.add_argument('--model-path',type=Path,required=True);args=parser.parse_args()
    if not args.memory_only and args.cache_root is None:parser.error('--cache-root is required unless --memory-only')
    if args.memory_only and args.cache_root is not None:parser.error('--memory-only does not accept --cache-root')
    worker_main(args.cache_root,args.model_path,memory_only=args.memory_only)
