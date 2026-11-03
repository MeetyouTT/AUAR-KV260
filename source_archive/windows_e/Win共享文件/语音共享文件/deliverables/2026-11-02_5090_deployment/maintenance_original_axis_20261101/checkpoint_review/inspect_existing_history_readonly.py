import json,hashlib,os
from pathlib import Path
base=Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9/state/kernel-history/archive')
current='903cfade-b93c-48fa-804e-379be1967313'
p=base/(current+'-5b26714b0be9d52bf99fe14c07a0f810105379171712328b63454beb314bc6bb.json')
rows=[];seen=set()
for depth in range(64):
 assert p.parent==base and p.resolve()==p and not p.is_symlink() and str(p) not in seen
 seen.add(str(p));raw=p.read_bytes();assert len(raw)<=262144
 v=json.loads(raw);cp=v['checkpoint'];seed=cp.get('seed',{})
 canon=(json.dumps(cp,sort_keys=True,separators=(',',':'))+'\n').encode()
 rows.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'archive_schema':v.get('schema'),'current_boot':v.get('current_boot'),'source_boot':v.get('source_boot'),'source_checkpoint_sha256':v.get('source_checkpoint_sha256'),'source_checkpoint_path':v.get('source_checkpoint_path'),'source_manifest_sha256':v.get('source_manifest_sha256'),'history_is_lower_bound':v.get('history_is_lower_bound'),'unknown_tail':v.get('unknown_tail'),'counter_scope':v.get('counter_scope'),'checkpoint_keys':sorted(cp),'checkpoint_schema':cp.get('schema'),'checkpoint_scope':cp.get('scope'),'checkpoint_boot':seed.get('boot_id',cp.get('boot_id')),'checkpoint_canonical_sha256':hashlib.sha256(canon).hexdigest(),'checkpoint_previous':cp.get('previous_kernel_history'),'seed_keys':sorted(seed),'auxiliary_keys':sorted(cp.get('auxiliary',{})),'legacy_top_keys':sorted(cp) if not seed else []})
 h=cp.get('previous_kernel_history')
 if h is None:break
 p=Path(h['archive_path'])
else:raise RuntimeError('chain exceeds review cap')
print(json.dumps({'actual_boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'archives':rows,'board_mutations':False,'project_imported':False,'devices_or_databases_opened':False}))
