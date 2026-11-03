"""Only read public sources and filtered metadata through strict trusted SSH."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
transport_path = OUT.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport_path.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('axis_face_contract_transport', transport_path)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
source = HERE / 'collect_face_diagnostic_contract_readonly.py'
raw = source.read_bytes()
result = json.loads(transport.ssh('python3 -B -', raw.decode('utf-8'), timeout=15))
output = HERE / 'FACE_DIAGNOSTIC_CONTRACT_READONLY.json'
with output.open('x', encoding='utf-8') as handle:
    json.dump({'host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'script_sha256': hashlib.sha256(raw).hexdigest(), 'board_result': result}, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({'output': str(output), 'packet': result['filtered_current_packet'],
                  'timing_value_types': result['detector_timing_value_types_only'],
                  'public_sources': {k: v['sha256'] for k, v in result['sources'].items()},
                  'board_mutations': False}, ensure_ascii=True))
