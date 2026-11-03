import hashlib,json,subprocess
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
c=json.loads(Path(json.loads((OPS/'meta.json').read_text())['candidate_config']).read_text())
p=Path(c['native_execution']['checkpoint_output']);a=json.loads(p.read_text())
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'checkpoint_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checkpoint_source_unit_sha256':a['source_unit_sha256'],'checkpoint_seed':{k:a['seed'].get(k) for k in ['boot_id','source_pid','source_birth_ticks','checkpoint_kind']},'zocl_refcnt':Path('/sys/module/zocl/refcnt').read_text().strip()}
raw=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],timeout=4)
d['unit_cat_sha256']=hashlib.sha256(raw).hexdigest();d['unit_cat']=raw.decode()
d['source_excerpts']={}
for path in [OPS/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py',OPS/'boot_ops.py']:
    lines=path.read_text().splitlines();selected=set()
    for i,line in enumerate(lines):
        if any(k in line for k in ['source_unit_sha','candidate_config','systemctl','checkpoint_output','unit_text','UNIT_SHA']):selected.update(range(max(0,i-3),min(len(lines),i+5)))
    d['source_excerpts'][str(path)]='\n'.join(str(i+1)+': '+lines[i] for i in sorted(selected))
print(json.dumps(d))
