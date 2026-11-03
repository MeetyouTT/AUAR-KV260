import datetime,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=Path('E:/Win共享文件/语音共享文件/deliverables/2026-10-18_board_dialogue/board_ssh.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_ssh',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=HERE/'collect_owner_supplement_readonly.py'
result=json.loads(m.ssh('python3 -B -',source.read_text(encoding='utf-8'),timeout=20))
out=dict(host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),board_result=result)
p=HERE/'OWNER_AND_RELEASE_SUPPLEMENT.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
