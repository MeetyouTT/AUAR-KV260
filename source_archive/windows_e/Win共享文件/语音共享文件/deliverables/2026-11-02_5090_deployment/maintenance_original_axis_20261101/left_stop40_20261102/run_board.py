"""Use the already verified strict SSH transport; save only numeric/code metadata."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

TRANSPORT = Path('E:/Win共享文件/语音共享文件/deliverables/2026-10-18_board_dialogue/board_ssh.py')
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('axis_strict_transport', TRANSPORT)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
script_path = Path(sys.argv[1])
result = transport.ssh('python3 -B -', script_path.read_text(encoding='utf-8'), timeout=55)
if isinstance(result, bytes):
    result = result.decode('utf-8')
value = json.loads(result)
output = Path(sys.argv[2])
assert not output.exists(), 'Keep earlier receipts'
output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
if len(sys.argv)>3 and sys.argv[3]=='--summary' and 'snapshots' in value:
    summary={k:v for k,v in value.items() if k!='snapshots'}
    summary['snapshot_count']=len(value['snapshots'])
    summary['latest']=value['snapshots'][-1] if value['snapshots'] else None
    print(json.dumps(summary,ensure_ascii=False,indent=2))
else:
    print(json.dumps(value, ensure_ascii=False, indent=2))
