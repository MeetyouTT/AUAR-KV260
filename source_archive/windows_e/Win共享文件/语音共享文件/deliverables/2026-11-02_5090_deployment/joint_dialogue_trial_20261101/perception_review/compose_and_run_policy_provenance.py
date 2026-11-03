"""Host-only public-policy provenance read. Preserves every prior observation."""
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'parallel_platform/gui_startup_review/collect_gui_post_start_metadata.py'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='654fa4eaee282d7c85b60d66a89df4ed732e5fe8cc60b7c584c50e6e12575824'
prefix=BASE.read_text(encoding='utf-8').split('samples=[]\nfor i in range(3):',1)[0]
source=prefix+'\n'+(HERE/'policy_provenance_tail.py.txt').read_text(encoding='utf-8')
ast.parse(source)
target=HERE/'collect_identity_policy_provenance.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
transport=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('identity_policy_readonly_ssh',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',source,timeout=75))
output=HERE/'identity_policy_provenance_01.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_observed_start_utc':start,'host_observed_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'transport_sha256':hashlib.sha256(transport.read_bytes()).hexdigest(),
        'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(output),'policy':result['direct_numeric_values'],
    'identity_config_sha256':result['identity_config_sha256'],
    'same_config_sha_in_old_23_new_24_and_actual':result['same_config_sha_in_old_23_new_24_and_actual'],
    'native_live_has_recognition_diagnostics_method':result['native_live_has_recognition_diagnostics_method'],
    'health_has_recognition_diagnostics_object':result['health_has_recognition_diagnostics_object'],
    'board_mutations':False}))
