"""Shallow inventory of the already installed original maintenance roots."""
import datetime
import hashlib
import json
from pathlib import Path

BOOT='903cfade-b93c-48fa-804e-379be1967313'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
roots=[Path('/home/root/aura-pan-wide-resume-20261029'),Path('/home/root/aura-system-pan-20261028'),
       Path('/home/root/aura-face-follow-test-20261101-bebd3e7d-r2'),
       Path('/home/root/aura-axis-priority-20261101-3c94e7a0')]
inventory={}
for root in roots:
    values=[]
    if root.is_dir():
        for path in sorted(root.iterdir(),key=lambda p:p.name):
            if path.is_symlink():continue
            item={'path':str(path),'directory':path.is_dir()}
            if path.is_file():
                item['bytes']=path.stat().st_size
                if path.suffix=='.py':item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.is_dir():
                children=[]
                for child in sorted(path.iterdir(),key=lambda p:p.name):
                    if child.is_file() and not child.is_symlink() and child.suffix in ('.py','.json'):
                        row={'path':str(child),'bytes':child.stat().st_size}
                        if child.suffix=='.py':row['sha256']=hashlib.sha256(child.read_bytes()).hexdigest()
                        children.append(row)
                item['direct_script_and_json_children']=children
            values.append(item)
    inventory[str(root)]=values
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
meta=json.loads((ops/'meta.json').read_bytes());state=json.loads((ops/'state.json').read_bytes())
print(json.dumps({'schema':'aura-original-maintenance-shallow-readonly-1','boot_id':BOOT,
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'roots':inventory,
    'ops_meta_sha256':hashlib.sha256((ops/'meta.json').read_bytes()).hexdigest(),
    'ops_source_boot':meta.get('source_boot'),'ops_old_camera_pid':meta.get('old_camera_pid'),
    'ops_state_phase':state.get('phase'),'ops_state_updated_boot':state.get('updated_boot'),
    'board_mutations':False,'project_imported':False,'device_opened':False,'database_opened':False}))
