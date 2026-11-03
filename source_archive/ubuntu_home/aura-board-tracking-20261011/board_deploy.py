import hashlib,json,subprocess
from pathlib import Path
stage=Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd');manifest=json.loads((stage/'payload/manifest.json').read_text())
model=Path(manifest['model_dependency']['model'])
model.parent.mkdir(parents=True,exist_ok=True)
blob=Path('/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel').read_bytes()
assert hashlib.sha256(blob).hexdigest()==manifest['model_dependency']['model_sha256']
if model.exists():assert model.read_bytes()==blob
else:model.write_bytes(blob)
config=model.with_suffix('.prototxt')
data=(stage/'payload/aura/models/dpu/yolox_nano_person.prototxt').read_bytes()
assert hashlib.sha256(data).hexdigest()==manifest['model_dependency']['model_config_sha256']
if config.exists():assert config.read_bytes()==data
else:config.write_bytes(data)
p=stage/'payload/board_apply.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files']['board_apply.py']['sha256']
result=subprocess.run(['python3','-B',str(p),'--phase','apply'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=140)
assert result.returncode==0,result.stdout
print(result.stdout)
