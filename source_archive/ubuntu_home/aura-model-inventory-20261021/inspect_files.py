"""Inventory local model sizes and saved Ollama metadata without loading models."""
import json, math, struct
from datetime import datetime, timezone
from pathlib import Path

root=Path('/home/ghmd/Win共享文件/语音共享文件')
out={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'unit':'decimal bytes; MB=1000000; GB=1000000000','files':[]}
for rel in ['aura/models/vision/yunet_2022mar.onnx','aura/models/vision/sface_2021dec.onnx','aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx','aura/models/tts/OmniVoice/model.safetensors','aura/models/tts/OmniVoice/audio_tokenizer/model.safetensors','deliverables/2026-10-18_identity_dpu/engineering-bee245f2a94e4d28/sface_engineering.xmodel']:
    p=root/rel
    v={'file':rel,'bytes':p.stat().st_size,'allocated_bytes':p.stat().st_blocks*512}
    if p.suffix=='.safetensors':
        with p.open('rb') as f:
            h=json.loads(f.read(struct.unpack('<Q',f.read(8))[0]))
        tensors=[t for k,t in h.items() if k!='__metadata__']
        v['stored_tensor_elements']=sum(math.prod(t['shape']) for t in tensors)
        v['note']='Stored tensor elements include buffers; not a strict trainable parameter count.'
    out['files'].append(v)
p=root/'deliverables/2026-10-18_latency_optimization/final_health.json'
out['ollama_saved_record']={'source':str(p.relative_to(root)),'live_windows_verified':False,'loaded_model':json.loads(p.read_text())['loaded_model']}
for name in ['probe','models','health']:
    p=Path(__file__).with_name(name+'.response.json')
    out[name+'_host_capture_utc']=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()
Path(__file__).with_name('files.response.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(out['files']),'checked_at_utc':out['checked_at_utc'],'ollama_size_bytes':out['ollama_saved_record']['loaded_model']['size']}))
