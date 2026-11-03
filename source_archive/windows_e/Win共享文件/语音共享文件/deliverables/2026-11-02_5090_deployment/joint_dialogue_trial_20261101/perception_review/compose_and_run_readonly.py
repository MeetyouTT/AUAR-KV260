"""Host-only composition of an already-reviewed metadata collector and strict SSH."""
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEPLOYMENT=HERE.parents[1]
BASE=DEPLOYMENT/'parallel_platform/gui_startup_review/collect_gui_post_start_metadata.py'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='654fa4eaee282d7c85b60d66a89df4ed732e5fe8cc60b7c584c50e6e12575824'
prefix=BASE.read_text(encoding='utf-8').split('samples=[]\nfor i in range(3):',1)[0]
assert 'owners[\'gtk\']=process(launch[\'pid\'])' in prefix
source=prefix+'\n'+(HERE/'perception_tail.py.txt').read_text(encoding='utf-8')
ast.parse(source)
target=HERE/'collect_joint_perception_02.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
TRANSPORT=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('joint_perception_strict_ssh',TRANSPORT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',source,timeout=75))
output=HERE/'perception_current_02.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_observed_start_utc':start,'host_observed_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'transport_sha256':hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(),'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(output),'status':result['status'],'checks':result['checks'],
                  'known_fresh_sample_count':result['known_fresh_sample_count'],
                  'final_identity_result_classification':result['samples'][-1]['perception']['identity_result_classification'],
                  'final_identity_diagnostic_reason':result['samples'][-1]['perception']['identity_diagnostic_reason'],
                  'board_mutations':False}))
