import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('remove_read_transport',transport);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
data=(HERE/'read_original_remove_result.py').read_bytes()
value=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=25))
output=HERE/'remove_result_01.json';assert not output.exists()
output.write_text(json.dumps({'script_sha256':hashlib.sha256(data).hexdigest(),'board_result':value},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
