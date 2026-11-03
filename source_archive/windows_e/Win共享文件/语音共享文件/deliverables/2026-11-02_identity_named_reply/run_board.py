"""One recorded submission through the existing strict board SSH transport."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

TASK = Path(__file__).resolve().parent
ROOT_THREAD = '01a1994e-f547-74e1-903d-3591021d67c8'
phase = json.loads((TASK / 'DEVICE_MAINTENANCE.json').read_text(encoding='utf-8'))
assert phase['permission_active'] and phase['operator_thread_id'] == ROOT_THREAD
registry = TASK.parent / '2026-11-02_5090_deployment/CHAT_COORDINATION.json'
owner = json.loads(registry.read_text(encoding='utf-8-sig'))['board_maintenance_owner']
assert owner['thread_id'] == ROOT_THREAD and owner['permission_active']
helper = TASK.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('existing_verified_board_transport', helper)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
script = TASK / sys.argv[1]
assert script.resolve().is_relative_to(TASK.resolve())
source = script.read_bytes()
compile(source, str(script), 'exec')
intent = TASK / (script.stem + '_HOST_INTENT.json')
result = TASK / (script.stem + '_RESULT.json')
assert not intent.exists() and not result.exists()
with intent.open('x', encoding='utf-8') as stream:
    json.dump(dict(host_utc=datetime.now(timezone.utc).isoformat(),
        script_sha256=hashlib.sha256(source).hexdigest(), single_submission=True), stream)
try:
    raw = transport.ssh('python3 -B -', source.decode('utf-8'), timeout=int(sys.argv[2]) if len(sys.argv) > 2 else 50)
    board = json.loads(raw)
    record = dict(host_utc=datetime.now(timezone.utc).isoformat(), board_result=board)
except Exception as error:
    record = dict(host_utc=datetime.now(timezone.utc).isoformat(), submission_outcome='UNCONFIRMED', error_class=type(error).__name__)
with result.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
summary = record.get('board_result', record)
print(json.dumps({key: summary[key] for key in ('status', 'errors', 'current_state', 'all380_actual_bytes_match',
    'startup_sha256', 'submission_outcome', 'error_class') if key in summary}, ensure_ascii=False))
if 'board_result' not in record:
    raise SystemExit(2)
