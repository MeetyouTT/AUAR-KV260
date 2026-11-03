"""Execute the read-only collector over the existing pinned project SSH transport."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TRANSPORT=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-10-18_board_dialogue\board_ssh.py')
raw=TRANSPORT.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('project_transport',TRANSPORT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=(HERE/'collect_camera_restore_readonly.py').read_bytes()
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
value=module.ssh('/usr/bin/python3 -B -I -S -',source.decode('utf-8'),timeout=40)
result=json.loads(value)
receipt={'host_start_utc':start,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'transport_sha256':hashlib.sha256(raw).hexdigest(),'collector_sha256':hashlib.sha256(source).hexdigest(),
         'remote_interpreter':['/usr/bin/python3','-B','-I','-S','-'],'board_result':result}
target=HERE/'CAMERA_RESTORE_READONLY_AUDIT.json'
with target.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps({'status':result['status'],'checks':result['checks'],'camera_owner':result['camera_owner'],
    'actual_run_config_path':result['actual_run_config_path'],'actual_run_config_sha256':result['actual_run_config_sha256'],
    'report':str(target)},ensure_ascii=True))
