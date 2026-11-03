"""Read the installed GUI's existing stop-command implementation only."""
import datetime
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
transport=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('original_axis_stop_api_source',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source="""import hashlib,json
from pathlib import Path
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(startup.read_bytes()).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
config=json.loads(startup.read_bytes());path=Path(config['runtime'])/'aura/tools/pan_controls.py'
raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert sha==config['component_sha256']['tools/pan_controls.py']
print(json.dumps({'path':str(path),'sha256':sha,'text':raw.decode(),'executed':False,'board_mutations':False}))
"""
value=json.loads(module.ssh('python3 -B -',source,timeout=20))
with (HERE/'original_stop_api_source_01.json').open('x',encoding='utf-8') as stream:
    json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_result':value},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'path':value['path'],'sha256':value['sha256'],'source_pinned':True}))
