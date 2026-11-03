import hashlib,json
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
b=json.loads(Path('/home/root/aura-hdmi-resume-20261029/c006a771-c3e4-4d4f-97d7-ade3dd774619/before.json').read_text())
d={'prestop_handoff':b['dpu_schedule'].get('protection_handoff')}
p=ops/'pan-face-edge-v5/native-operator-v1/identity_recovery.py';lines=p.read_text().splitlines();selected=set()
for i,line in enumerate(lines):
    if any(v in line for v in ['source_unit','configuration','native_execution','seed','checkpoint']):selected.update(range(max(0,i-2),min(len(lines),i+4)))
d['identity_recovery_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();d['identity_recovery_excerpt']='\n'.join(str(i+1)+': '+lines[i] for i in sorted(selected))
print(json.dumps(d))
