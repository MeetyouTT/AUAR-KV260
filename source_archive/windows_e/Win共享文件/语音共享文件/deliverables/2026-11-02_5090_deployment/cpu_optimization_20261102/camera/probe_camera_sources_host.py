"""Read only current camera owner, public source and technical config."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TRANSPORT=HERE.parent.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('camera_read_transport',TRANSPORT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import base64,hashlib,json,os,stat
from pathlib import Path
BOOT='903cfade-b93c-48fa-804e-379be1967313'
PID=79866
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
proc=Path('/proc')/str(PID)
cmd=(proc/'cmdline').read_bytes()
assert hashlib.sha256(cmd).hexdigest()=='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
assert int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])==2265436
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
def raw(path):
    path=Path(path)
    assert path.is_file() and not path.is_symlink(),str(path)
    assert path.suffix in ('.py','.json') and path.stat().st_size<=2000000
    return path.read_bytes()
meta=json.loads(raw(OPS/'meta.json'))
candidate=Path(meta['candidate_root'])
config_path=OPS/('native-run-'+BOOT+'-'+str(PID))/'config.json'
config_raw=raw(config_path); config=json.loads(config_raw)
entry=candidate/'aura/board/vision/ui_camera_service.py'
assert hashlib.sha256(raw(entry)).hexdigest()==meta['candidate_ui_sha256']
launch_entries=[Path(part.decode()) for part in cmd.split(bytes([0])) if part.startswith(b'/home/root/') and part.endswith(b'.py')]
assert len(launch_entries)==1
source_paths=[entry,launch_entries[0]]
files=[]
for path in source_paths:
    value=raw(path)
    files.append({'path':str(path),'sha256':hashlib.sha256(value).hexdigest(),'base64':base64.b64encode(value).decode()})
manifest_names=[str(p) for p in candidate.iterdir() if p.is_file() and ('manifest' in p.name or 'source' in p.name)]
print(json.dumps({'boot_id':BOOT,'owner':{'pid':PID,'birth_ticks':2265436,'command_sha256':hashlib.sha256(cmd).hexdigest()},
    'meta':meta,'candidate_root':str(candidate),'config_path':str(config_path),'config_sha256':hashlib.sha256(config_raw).hexdigest(),
    'config':{key:value for key,value in config.items() if key not in ('identity','face_gallery','gallery','native_execution')},
    'config_top_level_keys':sorted(config),'files':files,'candidate_manifest_names':manifest_names,
    'board_mutations':False,'device_or_db_opened':False}))
'''
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=25))
source_dir=HERE/'baseline';source_dir.mkdir(exist_ok=True)
import base64
for item in result.pop('files'):
    value=base64.b64decode(item.pop('base64'));assert hashlib.sha256(value).hexdigest()==item['sha256']
    path=source_dir/(item['sha256'][:12]+'__'+Path(item['path']).name)
    with path.open('xb') as stream:stream.write(value)
    item['local_path']=str(path)
    result.setdefault('source_files',[]).append(item)
with (HERE/'SOURCE_DISCOVERY.json').open('x',encoding='utf-8') as stream:
    json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_result':result},stream,indent=2)
print(json.dumps(result,ensure_ascii=True))
