import ast,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';C=H/'candidate_source'
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'));assert plan['status']=='CANDIDATE'
for name,row in plan['files'].items():
 raw=(C/name).read_bytes();ast.parse(raw.decode('utf-8'));row['candidate']=hashlib.sha256(raw).hexdigest()
ns={};exec((C/'common/voice_service_capabilities.py').read_text(encoding='utf-8'),ns)
d=hashlib.sha256()
for name in ns['SOURCE_FILES']:
 p=C/name
 if not p.exists():p=A/name
 d.update(name.encode()+b'\0');d.update(hashlib.sha256(p.read_bytes()).digest())
plan.update(candidate_revision=ns['SERVICE_REVISION'],candidate_fingerprint=d.hexdigest())
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(plan['candidate_fingerprint'])
