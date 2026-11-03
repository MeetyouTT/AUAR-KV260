"""Strict read-only host transport, with no remote command choice."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
source_path=HERE/'collect_policy_consumers_health.py'
transport=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('policy_consumers_readonly_ssh',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',source_path.read_text(encoding='utf-8'),timeout=75))
output=HERE/'policy_consumers_health_01.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_observed_start_utc':start,'host_observed_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(output),'gallery_count_publicly_available':result['gallery_count_publicly_available'],
    'public_health_gallery_counts':result['public_health_gallery_counts'],'public_health_gallery_availability':result['public_health_gallery_availability'],
    'board_mutations':False}))
