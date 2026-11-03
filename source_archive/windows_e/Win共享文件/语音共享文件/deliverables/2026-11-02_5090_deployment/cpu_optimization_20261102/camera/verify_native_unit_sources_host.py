import hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
helper=HERE.parent.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('unit_source_transport',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import hashlib,json
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1')
manifest_raw=(root/'source-manifest.json').read_bytes()
assert hashlib.sha256(manifest_raw).hexdigest()=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
manifest=json.loads(manifest_raw);rows=[]
for name,expected in manifest['files'].items():
    path=root/name
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<1000000,str(path)
    sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==expected,str(path)
    rows.append({'path':str(path),'sha256':sha})
library=root/'libaura_native_operator.so'
assert hashlib.sha256(library.read_bytes()).hexdigest()=='704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'
print(json.dumps({'source_unit_sha256':hashlib.sha256(manifest_raw).hexdigest(),'files_verified':rows,
    'native_library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'file_or_library_loaded':False,'board_mutations':False}))
'''
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
with (HERE/'NATIVE_UNIT_FILES_VERIFIED.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
