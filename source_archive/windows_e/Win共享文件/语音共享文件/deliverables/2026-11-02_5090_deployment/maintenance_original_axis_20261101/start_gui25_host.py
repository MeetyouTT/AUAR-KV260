"""Submit one normal GUI start after the restored camera binding transaction."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE / 'gui_binding_review/start_gui_after_restored_binding25.py'
expected = 'c0a213933781101cdef89b2d223a4b4f852de05257826b483557e269155c555e'
data = source.read_bytes()
assert hashlib.sha256(data).hexdigest() == expected
applied = json.loads((HERE / 'gui_binding25_applied.json').read_text(encoding='utf-8'))['board_result']
assert applied['status'] == 'SELECTED_BINDING_UPDATED_GUI_STILL_STOPPED'
transport = HERE.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
intent = HERE / 'gui_start25_host_intent.json'
output = HERE / 'gui_start25_request.json'
assert not intent.exists() and not output.exists()
with intent.open('x', encoding='utf-8') as handle:
    json.dump({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_sha256': expected,
               'action': 'one normal systemctl start --no-block aura-avatar-ui.service',
               'unknown_result_requires_readonly_reconciliation': True}, handle, indent=2)
spec = importlib.util.spec_from_file_location('gui25_root_transport', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
value = json.loads(module.ssh('python3 -B -', data.decode('utf-8'), timeout=30))
with output.open('x', encoding='utf-8') as handle:
    json.dump({'host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_sha256': expected,
               'board_result': value}, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
assert value['exit_code'] == 0 and value['start_requested'] is True
print(json.dumps({'start_requested_once': True, 'software_ready': False, 'receipt': str(output)}))
