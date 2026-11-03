import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
assert json.loads((HERE/'load_result_02.json').read_text(encoding='utf-8'))['board_result']['status']=='LOAD_CONFIRMED_ORIGINAL_WIDE_PLATFORM_ACTIVE'
assert json.loads((OUT/'axis_follow_restore/CURRENT_PHYSICAL_CONDITIONS.json').read_text(encoding='utf-8'))['user_confirmed_axis_motor_power_disconnected']
intent=HERE/'idstop_host_intent.json';output=HERE/'idstop_job_submission.json';assert not intent.exists() and not output.exists()
data=(HERE/'launch_original_idstop.py').read_bytes()
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('idstop_transport',transport);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
intent.write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':hashlib.sha256(data).hexdigest(),
    'unit':'aura-original-idstop-903c-v1.service','confirmation':'ID_STOP_ONLY','no_resend_on_unknown':True},indent=2)+'\n',encoding='utf-8')
value=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=30))
output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
