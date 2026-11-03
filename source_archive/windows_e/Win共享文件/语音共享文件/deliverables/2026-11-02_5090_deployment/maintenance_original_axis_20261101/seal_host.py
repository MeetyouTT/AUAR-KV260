import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
proof=json.loads((HERE/'checkpoint_review/FINAL_CHECKPOINT_VALIDATION.json').read_text(encoding='utf-8'))
assert proof['board_result']['original_python_validator_passed'] and proof['board_result']['full_previous_kernel_archive_chain_verified'] and proof['all_observed_sface_optional_recovery_lower_bounds_checked']
source=HERE/'seal_and_read_platform.py';data=source.read_bytes()
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('seal_transport',transport);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
output=HERE/'sealed_platform_before.json';assert not output.exists()
value=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=35))
output.write_text(json.dumps({'script_sha256':hashlib.sha256(data).hexdigest(),'board_result':value},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
