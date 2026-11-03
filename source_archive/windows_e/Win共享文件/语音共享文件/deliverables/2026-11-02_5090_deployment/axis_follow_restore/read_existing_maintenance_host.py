import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_original_maintenance_transport',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=HERE/'collect_existing_maintenance_readonly.py';raw=source.read_bytes()
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',raw.decode('utf-8'),timeout=35))
target=HERE/'existing_maintenance_inventory_01.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump({'host_start_utc':started,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256':hashlib.sha256(raw).hexdigest(),'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(target),'ops_source_boot':result['ops_source_boot'],
    'ops_state_phase':result['ops_state_phase'],
    'directories':{root:[p['path'] for p in values] for root,values in result['roots'].items()}}))
