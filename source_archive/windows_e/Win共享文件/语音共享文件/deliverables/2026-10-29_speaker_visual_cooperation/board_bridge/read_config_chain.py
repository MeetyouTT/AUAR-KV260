"""Fetch small service code/config, never a gallery, template, image or model."""
import base64,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'2026-10-29_audio_animation_polish'))
from board_guard import ssh
paths=[
 '/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json',
 '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/native_entry_operator.py',
 '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face_source.py',
]
if len(sys.argv)>1:paths=json.loads((H/sys.argv[1]).read_text())
assert all(Path(p).suffix in ('.py','.json') for p in paths)
script='''import base64,hashlib,json\nfrom pathlib import Path\nout={}\nfor name in NAMES:\n p=Path(name);raw=p.read_bytes();assert len(raw)<300000;out[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),raw=base64.b64encode(raw).decode())\nprint(json.dumps(out))'''.replace('NAMES',repr(paths))
values=json.loads(ssh('python3 -B -',script,timeout=20))
output=H/'camera_source';output.mkdir(exist_ok=True)
index=json.loads((H/'camera_source_index.json').read_text()) if (H/'camera_source_index.json').exists() else {}
for i,(path,value) in enumerate(values.items()):
 raw=base64.b64decode(value.pop('raw'));assert hashlib.sha256(raw).hexdigest()==value['sha256']
 name=hashlib.sha256(path.encode()).hexdigest()[:10]+'_'+Path(path).name
 (output/name).write_bytes(raw);index[path]=dict(value,local_name=name)
 print(json.dumps(dict(path=path,bytes=len(raw),**value)))
(H/'camera_source_index.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
