"""Root-only single submission of the reviewed restored-camera binding update."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE / 'gui_binding_review/apply_gui_binding25.py'
expected = '34b6eafb5fd03f6571ff7f65c2102cddc615309293acbed21cf96c955f32a1e1'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected
audit = json.loads((HERE / 'camera_restore_audit/RESTORED_CAMERA_AUDIT.json').read_text(encoding='utf-8'))['board_result']
assert audit['status'] == 'PASS' and len(audit['checks']) == 21 and all(audit['checks'].values())
transport = HERE.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
intent = HERE / 'gui_binding25_host_intent.json'
output = HERE / 'gui_binding25_applied.json'
assert not intent.exists() and not output.exists()
with intent.open('x', encoding='utf-8') as handle:
    json.dump({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'script_sha256': expected,
               'command': 'python3 -B - --apply-selected-restored-camera-binding',
               'unknown_result_requires_readonly_reconciliation': True}, handle, indent=2)
spec = importlib.util.spec_from_file_location('binding25_root_transport', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
value = json.loads(module.ssh('python3 -B - --apply-selected-restored-camera-binding', raw.decode('utf-8'), timeout=45))
receipt = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_sha256': expected, 'board_result': value}
with output.open('x', encoding='utf-8') as handle:
    json.dump(receipt, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
assert value['status'] == 'SELECTED_BINDING_UPDATED_GUI_STILL_STOPPED'
assert value['post_component_sha256_verified'] and value['post_original_verifier_passed']
assert value['original_source_pins_preserved'] == 24 and value['candidate_source_files_verified'] == 25
assert value['startup_after_sha256'] == '3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'
assert value['ui_after_sha256'] == 'fc98455a5586cc4f1896f5472ec9b204bd7ff2b0c5be2798ba5cab1788b9b959'
print(json.dumps({'status': value['status'], 'components': value['components_verified'],
                  'source_pins': value['candidate_source_files_verified'], 'camera_pid': value['camera_owner']['pid']}))
