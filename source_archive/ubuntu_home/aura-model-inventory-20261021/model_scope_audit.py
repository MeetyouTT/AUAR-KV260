"""Check whether the active audio frontend introduces another learned model."""
import json,subprocess
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0');cfg=Path(args[args.index('--config')+1]);v=json.loads(cfg.read_text())
root=cfg.parent.parent/'runtime/aura'
out={'active_root':str(root),'startup_keys':list(v),'audio_sources':{},'extra_model_references':[],'model_files':[]}
for p in root.rglob('*.py'):
    if any(x in p.parts for x in ['tests','fixtures','site-packages']):continue
    if not any(x in str(p.relative_to(root)).lower() for x in ['audio','frontend','vad','kws','voice']):continue
    lines=p.read_text().splitlines()
    if any(x in p.name for x in ['frontend','vad','automatic_capture']):
        selected=[str(i+1)+': '+s for i,s in enumerate(lines) if any(t in s.lower() for t in ['import ','def ','rms','energy','threshold','silero','webrtc','onnx','model','vad'])]
        out['audio_sources'][str(p.relative_to(root))]='\n'.join(selected)[:4500]
    for i,s in enumerate(lines):
        if any(t in s.lower() for t in ['silero','webrtcvad','zipformer','.onnx','keywordspotter','energyvad']):
            out['extra_model_references'].append({'file':str(p.relative_to(root)),'line':i+1,'text':s.strip()})
for p in root.rglob('*'):
    if p.is_file() and p.suffix in ['.onnx','.xmodel','.safetensors','.gguf','.pt','.pth']:
        out['model_files'].append({'file':str(p.relative_to(root)),'bytes':p.stat().st_size})
out['extra_model_references']=out['extra_model_references'][:35]
print(json.dumps(out),flush=True)
