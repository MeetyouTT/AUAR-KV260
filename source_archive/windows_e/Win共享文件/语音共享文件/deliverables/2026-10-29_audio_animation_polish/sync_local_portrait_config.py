"""Pin the same revision for future root launches; preserve every other setting."""
import hashlib,json,os,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];name='aura/config/board_avatar_gtk.json';path=P/name
report=json.loads((H/'source_installation.json').read_text(encoding='utf-8'));assert name not in report['files']
old=path.read_bytes();v=json.loads(old)
if 'portrait_offload' not in v:
    (H/'local_config_sync.json').write_text(json.dumps({'status':'NOT_APPLICABLE','reason':'Unused legacy local config has no offload; actual board staged config and canonical host config are pinned separately','changed':False},indent=2),encoding='utf-8')
    print(json.dumps({'status':'NOT_APPLICABLE','changed':False}));raise SystemExit(0)
previous=dict(v['portrait_offload'])
v['portrait_offload']['revision']=json.loads((H/'snapshot_verification.json').read_text())['revision']
assert {k:value for k,value in v['portrait_offload'].items() if k!='revision'}=={k:value for k,value in previous.items() if k!='revision'}
raw=json.dumps(v,indent=2).encode();backup=H/'source_backup'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old)
report['files'][name]={'before':hashlib.sha256(old).hexdigest(),'after':hashlib.sha256(raw).hexdigest()}
temporary=path.with_name(path.name+'.audio-animation-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,path)
(H/'source_installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','only_portrait_revision_changed':True}))
