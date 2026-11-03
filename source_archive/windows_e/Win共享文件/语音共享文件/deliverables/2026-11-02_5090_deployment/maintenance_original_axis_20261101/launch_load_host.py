import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
proof=json.loads((HERE/'checkpoint_review/FINAL_CHECKPOINT_VALIDATION.json').read_text(encoding='utf-8'))
assert proof['board_result']['full_previous_kernel_archive_chain_verified'] and proof['all_observed_sface_optional_recovery_lower_bounds_checked']
assert json.loads((HERE/'sealed_platform_before.json').read_text(encoding='utf-8'))['board_result']['original_bytes_unchanged']
assert json.loads((OUT/'axis_follow_restore/CURRENT_PHYSICAL_CONDITIONS.json').read_text(encoding='utf-8'))['user_confirmed_axis_motor_power_disconnected']
assert json.loads((HERE/'remove_result_02.json').read_text(encoding='utf-8'))['board_result']['status']=='REMOVE_CONFIRMED_AND_ACTUAL_PLATFORM_UNLOADED'
intent=HERE/'load_host_intent.json';output=HERE/'load_job_submission.json';assert not intent.exists() and not output.exists()
data=(HERE/'launch_original_load.py').read_bytes()
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('remove_transport',transport);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
intent.write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':hashlib.sha256(data).hexdigest(),
    'unit':'aura-original-load-903c-v1.service','no_resend_on_unknown':True},indent=2)+'\n',encoding='utf-8')
value=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=30))
output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
