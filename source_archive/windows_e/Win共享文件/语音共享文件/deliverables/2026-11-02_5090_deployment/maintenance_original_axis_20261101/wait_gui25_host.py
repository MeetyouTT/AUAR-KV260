"""Readiness wait is observation only; it never resubmits the GUI start."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE.parent / 'identity_dialogue_review/restart_v2_review/wait_for_gui_ready_90.py'
data = source.read_bytes()
assert hashlib.sha256(data).hexdigest() == '1876cd91c638ef8c0115861d86061ab0bfd90bfce7049c55619ef5cbdd95fa28'
assert (HERE / 'gui_start25_request.json').exists()
transport = HERE.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('gui25_wait_transport', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
value = json.loads(module.ssh('python3 -B -', data.decode('utf-8'), timeout=105))
output = HERE / 'gui_ready25_wait.json'
with output.open('x', encoding='utf-8') as handle:
    json.dump({'host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'board_result': value}, handle, indent=2)
    handle.write('\n')
print(json.dumps(value))
