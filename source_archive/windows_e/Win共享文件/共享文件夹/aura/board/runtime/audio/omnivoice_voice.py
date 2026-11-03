"""Host-only OmniVoice 16-step voice, isolated cache and exact selected reference."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys
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

    def __init__(self,cache_root,model_path,voice_root=VOICE):
        if not model_path:raise ValueError('Configure the local OmniVoice model directory')
        super().__init__(cache_root,model_path,voice_root)
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

def worker_main(cache_root,model_path):
    sys.stdout.reconfigure(encoding='utf-8');sys.stdin.reconfigure(encoding='utf-8')
    synth=OmniVoiceSynthesizer(cache_root,model_path)
    for line in sys.stdin:
        try:
            request=json.loads(line)
            if request.get('type')=='warmup':
                import torch
                synth.load();torch.manual_seed(8701)
                # Always run inference: a cached short clip cannot warm CUDA kernels.
                with torch.inference_mode():synth.generate_waves('嗯，我在呢。')
                torch.cuda.synchronize();result={'ready':True}
            else:result=synth.synthesize(request['text'])
            print('RESULT '+json.dumps({'ok':True,'result':result},ensure_ascii=False),flush=True)
        except Exception as exc:
            print('RESULT '+json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--cache-root',type=Path,required=True)
    parser.add_argument('--model-path',type=Path,required=True);args=parser.parse_args()
    worker_main(args.cache_root,args.model_path)
