"""One read-only source/technical-manifest batch, explicitly permitted by root."""
import base64,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
helper=HERE.parent.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('contract_transport',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import base64,hashlib,json
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=OPS/'pan-face-edge-v5';OP=F/'native-operator-v1'
meta=json.loads((OPS/'meta.json').read_bytes())
runtime_raw=(OP/'runtime-manifest.json').read_bytes();runtime=json.loads(runtime_raw)
assert len(runtime['files'])==7
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in runtime['files'].items())
paths=[OPS/'build_plan.py',OPS/'equivalence_benchmark.py',F/'camera_wrapper.py',OP/'identity_recovery.py']
files=[]
for path in paths:
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=1000000
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    pin=runtime['files'].get(str(path)) or meta['source_pins'].get(path.name)
    if path.name=='camera_wrapper.py':pin='065c465e0ad0d8cf3ada4b69dcc422a4f85a286b1a7be1536e29d4aeac562df8'
    assert pin==sha
    files.append({'path':str(path),'sha256':sha,'base64':base64.b64encode(raw).decode()})
settings=json.loads((OP/'settings.json').read_bytes())
config_path=OPS/'native-run-903cfade-b93c-48fa-804e-379be1967313-79866/config.json'
native=json.loads(config_path.read_bytes())['native_execution']
library_root=Path(meta['native_library']).parent
library_metadata=[{'name':p.name,'bytes':p.stat().st_size} for p in library_root.iterdir() if p.is_file()]
print(json.dumps({'runtime_manifest_sha256':hashlib.sha256(runtime_raw).hexdigest(),'runtime_manifest':runtime,
    'settings':{key:value for key,value in settings.items() if any(s in key for s in ('unit','source','config','library','manifest','boot','mode','enabled'))},
    'native_execution':native,'files':files,'native_library_root':str(library_root),'native_library_metadata':library_metadata,
    'board_mutations':False,'services_or_device_or_model_touched':False}))
'''
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=25))
for row in result.pop('files'):
    raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256']
    path=HERE/'baseline'/(row['sha256'][:12]+'__'+Path(row['path']).name)
    with path.open('xb') as stream:stream.write(raw)
    row['local_path']=str(path);result.setdefault('source_files',[]).append(row)
with (HERE/'DEPLOYMENT_CONTRACT_DISCOVERY.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result,ensure_ascii=True))
