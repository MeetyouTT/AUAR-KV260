import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
transport=Path('E:/Win共享文件/语音共享文件/deliverables/2026-10-18_board_dialogue/board_ssh.py')
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_strict_ssh',transport);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=HERE/'collect_axis_new_boot_readonly.py';started=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',source.read_text(encoding='utf-8'),timeout=50))
out=dict(host_started_utc=started,host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),board_result=result)
p=HERE/'FRESH_NEW_BOOT_ASSESSMENT.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=str(p),host_utc=out['host_utc'],boot_id=result['boot_id'],startup_sha256=result['startup_sha256_after'],
    platform=result['platform'],compatibility=result['compatibility'],gui=result['gui'],
    components_count=result['components_count'],bad_components=result['bad_components'],
    controller_count=result['controller_file_count'],bad_controller_files=result['bad_controller_files'],
    owners=result['owners'],selected_face_readback=result['selected_face_readback'],board_mutations=False),indent=2))
