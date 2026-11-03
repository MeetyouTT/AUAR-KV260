"""Make the normal launcher test the canonical current host config."""
import hashlib,json,os,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];name='start_voice.ps1';path=P/name
r=json.loads((H/'source_installation.json').read_text(encoding='utf-8'));assert name not in r['files']
prior=path.read_bytes();old=b'deliverables/2026-10-27_windows_portrait/host_config.json';new=b'aura/config/portrait_host.local.json'
assert prior.count(old)==1
raw=prior.replace(old,new)
backup=H/'source_backup'/name;backup.write_bytes(prior)
temporary=path.with_name(path.name+'.portrait-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,path)
r['files'][name]={'before':hashlib.sha256(prior).hexdigest(),'after':hashlib.sha256(raw).hexdigest()}
(H/'source_installation.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','normal_launcher_uses_canonical_portrait_config':True,'voice_backend_changed':False}))
