import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
transport=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_original_readonly_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=HERE/'collect_original_axis_readonly.py';raw=source.read_bytes()
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',raw.decode('utf-8'),timeout=60))
target=HERE/'original_axis_inventory_01.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump({'host_start_utc':started,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256':hashlib.sha256(raw).hexdigest(),'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(target),'startup_sha256':result['startup_sha256'],
    'manual_config':result['manual_config'],'face_config':result['face_config'],
    'controllers':{k:{'manifest_sha256':v['manifest_sha256'],'all_match':v['all_match'],'count':len(v['files'])} for k,v in result['controllers'].items()},
    'sources_read':len(result['sources'])}))
