"""Root-owned, single-use application of the reviewed metadata transaction."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE/'parallel_platform/gui_startup_review/apply_gui_selected_binding.py'
OUTPUT = HERE/'gui_selected_binding_applied.json'
assert not OUTPUT.exists()
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '90457b126404264977345c186c8ce9aa6f36c6973c4f76e696043cb722fb05b6'
transport = HERE.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('root_strict_board_transport', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
response = module.ssh('python3 -B - --apply-selected-current-binding', raw.decode('utf-8'), timeout=50)
receipt = json.loads(response)
with OUTPUT.open('x', encoding='utf-8') as stream:
    json.dump({'host_start_utc':start,
        'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'transaction_script_sha256':hashlib.sha256(raw).hexdigest(),
        'board_result':receipt}, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
assert receipt['status'] == 'SELECTED_BINDING_UPDATED_GUI_STILL_STOPPED'
assert receipt['post_component_sha256_verified'] and receipt['post_original_verifier_passed']
assert receipt['old_selected_binding_unchanged'] and receipt['default_14_pin_binding_unchanged']
assert receipt['services_started'] is False
print(json.dumps({'output':str(OUTPUT), 'status':receipt['status'],
    'startup_after_sha256':receipt['startup_after_sha256'],
    'ui_after_sha256':receipt['ui_after_sha256'], 'services_started':False}))
