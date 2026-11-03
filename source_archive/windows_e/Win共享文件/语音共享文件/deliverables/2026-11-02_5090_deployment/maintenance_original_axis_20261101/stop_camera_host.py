import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
assert json.loads((OUT/'axis_follow_restore/CURRENT_PHYSICAL_CONDITIONS.json').read_text(encoding='utf-8'))['user_confirmed_axis_motor_power_disconnected']
assert json.loads((HERE/'identity_query_applied.json').read_text(encoding='utf-8'))['board_result']['status']=='IDENTITY_QUERY_V2_UPDATED_GUI_STILL_STOPPED'
pre=json.loads((HERE/'checkpoint_review/prestop_current_01.json').read_text(encoding='utf-8'))['board_result']
assert pre['phase']=='READONLY_PREFLIGHT_OK_NORMAL_CAMERA_STOP_STILL_REQUIRED'
source=HERE/'stop_original_camera.py';data=source.read_bytes()
intent_path=HERE/'camera_stop_host_intent.json';output=HERE/'camera_stop_receipt.json'
assert not intent_path.exists() and not output.exists()
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('camera_stop_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
intent_path.write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'script_sha256':hashlib.sha256(data).hexdigest(),'normal_stop_once':True,'observe_before_retry':True},indent=2)+'\n',encoding='utf-8')
value=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=45))
output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
