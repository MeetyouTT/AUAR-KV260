import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
assert json.loads((HERE/'gui_stop_receipt.json').read_text(encoding='utf-8'))['status']=='GUI_STOPPED'
source=OUT/'identity_dialogue_collaboration/apply_identity_query_v2.py';data=source.read_bytes()
assert hashlib.sha256(data).hexdigest()=='0ab6383fd78192a230aaa85a24a6c841d9417586bce28014989d0b795e5af1ae'
candidate=OUT/'identity_dialogue_collaboration/candidate/tools/unified_identity_binding.py'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('identity_apply_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
output=HERE/'identity_query_applied.json';assert not output.exists()
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
value=json.loads(module.ssh('python3 -B - --apply-identity-query-v2',data.decode('utf-8'),timeout=45))
output.write_text(json.dumps({'host_start_utc':started,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'script_sha256':hashlib.sha256(data).hexdigest(),'board_result':value},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert value['status']=='IDENTITY_QUERY_V2_UPDATED_GUI_STILL_STOPPED'
assert value['component_count_verified']==380 and value['selected_binding_verified'] and value['camera_owner_unchanged']
print(json.dumps({'status':value['status'],'startup_after_sha256':value['startup_after_sha256'],'components':380,
    'camera_owner_unchanged':True,'output':str(output)}))
