import base64
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TRANSPORT=HERE.parent.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('ingress_transport',TRANSPORT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import base64,hashlib,json
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
F=OPS/'pan-face-edge-v5';ROOT=F/'face-source-v17'
assert hashlib.sha256((ROOT/'entry.py').read_bytes()).hexdigest()=='f26be22cb640bf44a1bd81b66bb3fa014f5b847b13320781836bf3f173387623'
manifest_raw=(ROOT/'deployment-manifest.json').read_bytes();manifest=json.loads(manifest_raw)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in manifest['pins'].items())
meta=json.loads((OPS/'meta.json').read_bytes());candidate=Path(meta['candidate_root'])
names=['entry.py','raw_capture.py','face_source.py','face_observation.py','face_lock.py','face_timing.py','stage_timing.py','fast_yunet_input.py','direct_yunet_input.py','native_entry_operator.py','local_preview.py','camera_device.py','pipeline_metrics.py','native_protection.py','native_boot.py']
paths=[]
for name in names:
    choices=[ROOT/name,F/name,F/'native-operator-v1'/name,candidate/'aura/board/vision'/name]
    path=next((p for p in choices if p.is_file()),None)
    if path is not None:paths.append(path)
files=[]
for path in paths:
    assert not path.is_symlink() and path.stat().st_size<=1000000
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if str(path) in manifest['pins']:assert manifest['pins'][str(path)]==sha
    elif str(path) in meta['protected']:assert meta['protected'][str(path)]==sha
    elif str(path) in meta.get('candidate_pins',{}):assert meta['candidate_pins'][str(path)]==sha
    files.append({'path':str(path),'sha256':sha,'base64':base64.b64encode(raw).decode()})
print(json.dumps({'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'manifest':manifest,
    'files':files,'board_mutations':False,'device_or_db_opened':False}))
'''
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=30))
source_dir=HERE/'baseline';source_dir.mkdir(exist_ok=True)
for item in result.pop('files'):
    value=base64.b64decode(item.pop('base64'));assert hashlib.sha256(value).hexdigest()==item['sha256']
    path=source_dir/(item['sha256'][:12]+'__'+Path(item['path']).name)
    if path.exists():assert path.read_bytes()==value
    else:
        with path.open('xb') as stream:stream.write(value)
    item['local_path']=str(path)
    result.setdefault('source_files',[]).append(item)
with (HERE/'INGRESS_SOURCE_MANIFEST.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({'manifest_sha256':result['manifest_sha256'],'files':[{k:v for k,v in row.items() if k!='local_path'} for row in result['source_files']],'pins_verified':len(result['manifest']['pins'])}))
