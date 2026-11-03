"""Execute only default dry-run branch, without forwarding any command-line arguments."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TRANSPORT=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
SOURCE=HERE/'apply_gui_selected_binding.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == '90457b126404264977345c186c8ce9aa6f36c6973c4f76e696043cb722fb05b6'
spec=importlib.util.spec_from_file_location('gui_readonly_transaction_transport',TRANSPORT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',SOURCE.read_text(encoding='utf-8'),timeout=75))
assert result['status'] == 'DRY_RUN_READY' and result['board_mutations'] is False
assert result['services_started'] is False and result['database_opened_or_copied'] is False
output=HERE/'gui_binding_transaction_dryrun_01.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_observed_start_utc':start,'host_observed_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'script_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(output),'status':result['status'],'board_mutations':False}))
