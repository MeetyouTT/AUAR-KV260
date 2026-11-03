import base64,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
transport=HERE.parent.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('extra_transport',transport);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import base64,hashlib,http.client,json,subprocess
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');ROOT=OPS/'pan-face-edge-v5/face-source-v17'
meta=json.loads((OPS/'meta.json').read_bytes());candidate=Path(meta['candidate_root'])
manifest=json.loads((ROOT/'deployment-manifest.json').read_bytes())
paths=[ROOT/'face_flow.py',OPS/'native_entry_pan_face_v5.py']+[candidate/'aura'/name for name in ('board/identity/face_targets.py','board/identity/camera_faces.py','board/vision/native_startup.py','board/vision/reference_faces.py')]
files=[]
for path in paths:
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=1000000
    value=path.read_bytes();sha=hashlib.sha256(value).hexdigest()
    pin=manifest['pins'].get(str(path)) or meta.get('candidate_pins',{}).get(str(path)) or meta['protected'].get(str(path))
    if pin:assert sha==pin
    files.append({'path':str(path),'sha256':sha,'verified_manifest_pin':pin,'base64':base64.b64encode(value).decode()})
p=subprocess.run(['gst-inspect-1.0','videoconvert'],capture_output=True,text=True,timeout=5)
properties=[]
if p.returncode==0:
    lines=p.stdout.splitlines()
    for index,line in enumerate(lines):
        if any(fragment in line for fragment in ('n-threads','qos','dither','chroma-resampler','matrix-mode','gamma-mode','primaries-mode')):properties.extend(lines[index:index+5])
connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=2)
try:
    connection.request('GET','/health');response=connection.getresponse();h=json.loads(response.read(2097153));assert response.status==200
finally:connection.close()
def numeric(value,depth=0):
    if not isinstance(value,dict) or depth>7:return {}
    return {k:numeric(v,depth+1) if isinstance(v,dict) else v for k,v in value.items() if isinstance(v,dict) or type(v) in (bool,int,float) or v is None}
identity=h.get('identity',{})
timings={k:numeric(v) for k,v in identity.items() if isinstance(v,dict) and any(s in k for s in ('timing','metric','flow','target'))}
print(json.dumps({'files':files,'videoconvert_properties':properties,'health_keys':sorted(h),'identity_timing_keys':sorted(timings),'timings':timings,'pipeline_metrics':numeric(h.get('pipeline_metrics',{})),'board_mutations':False,'device_or_db_opened':False}))
'''
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=25))
for item in result.pop('files'):
    value=base64.b64decode(item.pop('base64'));assert hashlib.sha256(value).hexdigest()==item['sha256']
    path=HERE/'baseline'/(item['sha256'][:12]+'__'+Path(item['path']).name)
    if path.exists():assert path.read_bytes()==value
    else:
        with path.open('xb') as stream:stream.write(value)
    item['local_path']=str(path);result.setdefault('source_files',[]).append(item)
with (HERE/'EXTRA_SOURCE_MANIFEST.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result,ensure_ascii=True))
