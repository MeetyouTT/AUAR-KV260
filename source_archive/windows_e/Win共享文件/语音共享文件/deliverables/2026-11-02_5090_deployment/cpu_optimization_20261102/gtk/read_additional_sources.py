import base64
import hashlib
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
helper=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('additional_transport',helper)
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
code='''import base64,hashlib,json
from pathlib import Path
base=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
raw=base.read_bytes();doc=json.loads(raw);aura=Path(doc['runtime'])/'aura';pins=doc['component_sha256']
names=('board/interaction/ui_services.py','board/vision/local_preview.py','tools/native_video.py','tests/framework/test_local_camera_preview.py','tests/framework/test_board_ui_services.py')
output={}
for name in names:
    assert name in pins
    source=(aura/name).read_bytes();assert hashlib.sha256(source).hexdigest()==pins[name]
    output[name]={'sha256':pins[name],'data':base64.b64encode(source).decode()}
assert base.read_bytes()==raw
print(json.dumps({'startup_sha256':hashlib.sha256(raw).hexdigest(),'files':output}))
'''
value=json.loads(transport.ssh('/usr/bin/python3 -B -I -S -',code,timeout=15))
meta={'startup_sha256':value['startup_sha256'],'source_sha256':{}}
for name,content in value['files'].items():
    path=HERE/'original'/name;path.parent.mkdir(parents=True,exist_ok=True)
    data=base64.b64decode(content['data']);assert hashlib.sha256(data).hexdigest()==content['sha256']
    with path.open('xb') as stream:stream.write(data)
    meta['source_sha256'][name]=content['sha256']
with (HERE/'SOURCE_ADDITIONAL.json').open('x',encoding='utf-8') as stream:json.dump(meta,stream,indent=2)
print(json.dumps(meta))
