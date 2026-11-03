"""Invoke the reviewed metadata-only script through the trusted transport."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
TRANSPORT = OUT.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('axis_config_readonly_transport', TRANSPORT)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
source = HERE / 'collect_axis_config_readonly.py'
raw = source.read_bytes()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = json.loads(transport.ssh('python3 -B -', raw.decode('utf-8'), timeout=40))
output = HERE / 'CURRENT_AXIS_CONFIG_READONLY.json'
with output.open('x', encoding='utf-8') as handle:
    json.dump({'host_start_utc': started, 'host_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'script_sha256': hashlib.sha256(raw).hexdigest(), 'board_result': result}, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({'output': str(output), 'startup_sha256': result['startup_sha256'],
                  'current_platform': result['current_platform'],
                  'current_boot_manual_binding_valid': result['current_boot_manual_binding_valid'],
                  'current_boot_direction_evidence': result['current_boot_direction_evidence'],
                  'current_boot_zone_binding_valid': result['current_boot_zone_binding_valid'],
                  'board_mutations': False}, ensure_ascii=True))
