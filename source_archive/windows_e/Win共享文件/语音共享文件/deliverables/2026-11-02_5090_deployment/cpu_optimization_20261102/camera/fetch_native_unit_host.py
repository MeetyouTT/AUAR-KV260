import hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
helper=HERE.parent.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('unit_manifest_transport',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
code=r'''
import hashlib,json
from pathlib import Path
path=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/source-manifest.json')
assert path.is_file() and not path.is_symlink() and path.stat().st_size<1000000
raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
report=Path('/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/report.json')
assert report.is_file() and not report.is_symlink() and report.stat().st_size<1000000
print(json.dumps({'unit_manifest_path':str(path),'unit_manifest_sha256':hashlib.sha256(raw).hexdigest(),'unit_manifest':json.loads(raw),'predecessor_library_report':json.loads(report.read_bytes()),'board_mutations':False}))
'''
result=json.loads(module.ssh('/usr/bin/python3 -B -I -S -',code,timeout=20))
with (HERE/'NATIVE_UNIT_PROVENANCE.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result,ensure_ascii=True))
