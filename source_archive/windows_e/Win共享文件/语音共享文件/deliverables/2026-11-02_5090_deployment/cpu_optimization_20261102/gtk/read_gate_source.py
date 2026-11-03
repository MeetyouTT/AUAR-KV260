import base64,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
helper=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('gate_transport',helper)
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
code='''import base64,hashlib,json
from pathlib import Path
path=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
raw=path.read_bytes();doc=json.loads(raw);root=Path(doc['runtime'])/'aura';name='board/interaction/ui_contract.py'
assert doc['component_sha256']['board/interaction/ui_services.py']=='b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711'
data=(root/name).read_bytes();digest=hashlib.sha256(data).hexdigest();assert digest==doc['component_sha256'][name]
assert path.read_bytes()==raw
print(json.dumps({'name':name,'sha256':digest,'startup_sha256':hashlib.sha256(raw).hexdigest(),'data':base64.b64encode(data).decode()}))
'''
value=json.loads(transport.ssh('/usr/bin/python3 -B -I -S -',code,timeout=12))
raw=base64.b64decode(value.pop('data'));assert hashlib.sha256(raw).hexdigest()==value['sha256']
target=HERE/'original'/value['name'];target.parent.mkdir(parents=True,exist_ok=True)
with target.open('xb') as stream:stream.write(raw)
with (HERE/'SOURCE_GATE.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(value))
