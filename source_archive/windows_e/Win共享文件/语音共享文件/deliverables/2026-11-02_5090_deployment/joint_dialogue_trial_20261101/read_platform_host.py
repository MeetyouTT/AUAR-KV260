import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
transport=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('joint_readonly_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=HERE/'read_platform_live.py';raw=source.read_bytes()
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
value=json.loads(module.ssh('python3 -B -',raw.decode('utf-8'),timeout=35))
output=HERE/'platform_live_01.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_start_utc':started,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':hashlib.sha256(raw).hexdigest(),'board_result':value},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(output),'board_result':value}))
