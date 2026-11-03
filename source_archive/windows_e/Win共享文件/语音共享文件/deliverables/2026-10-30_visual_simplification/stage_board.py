"""Stage only the retired uploader stub; no camera, microphone or motion changes."""
import base64,hashlib,json
from pathlib import Path
from maintenance import H,read,save,capture,same
from board_guard import ssh
b=read('board_after_rollback.json') if (H/'board_after_rollback.json').exists() else read('baseline.json')['board']
same(b,capture());same(b,capture());save('board_stage_baseline.json',b)
payload=(H/'board/device_observer.py').read_bytes();sha=hashlib.sha256(payload).hexdigest()
script=r'''
import base64,hashlib,importlib.util,json,shutil
from pathlib import Path
b=BASE;raw=base64.b64decode(PAYLOAD)
stage=Path('/home/root/aura-board-vision-20261030')/(SHA[:16]+'-r2')
assert stage.resolve().is_relative_to(Path('/home/root/aura-board-vision-20261030'))
assert not stage.exists(),'Do not overwrite a prior candidate'
root=stage/'runtime';startup=stage/'startup'
shutil.copytree(Path(b['actual_runtime']),root,symlinks=True,ignore=shutil.ignore_patterns('managed-runs','__pycache__'))
startup.mkdir()
launcher=Path(b['pending_launcher']).read_bytes()
assert hashlib.sha256(launcher).hexdigest()==b['pending_launcher_sha256']
(startup/'launcher.py').write_bytes(launcher)
target=root/'aura/board/runtime/device_observer.py'
assert not target.is_symlink() and target.resolve().is_relative_to(root.resolve())
target.write_bytes(raw)
assert hashlib.sha256(target.read_bytes()).hexdigest()==SHA
cfg=dict(b['pending']);pins=dict(b['pins']);pins['board/runtime/device_observer.py']=SHA
cfg.update(runtime=str(root),component_sha256=pins)
(startup/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
for name,value in pins.items():assert hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()==value,name
spec=importlib.util.spec_from_file_location('retired_upload',target)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
observer=module.DeviceObserver('SYNTHETIC_ONLY');observer.enabled=True
state=observer.public();observer.close()
assert state['enabled'] is False and state['sent']==0 and state['image_upload_enabled'] is False
print(json.dumps(dict(status='STAGED',stage=str(stage),runtime=str(root),startup=str(startup),pins=pins,
 changed=['board/runtime/device_observer.py'],arm_stub_test=state)))
'''.replace('BASE',repr(b)).replace('PAYLOAD',repr(base64.b64encode(payload).decode())).replace('SHA',repr(sha))
c=json.loads(ssh('python3 -B -',script,timeout=50));save('board_candidate.json',c)
print(json.dumps({'status':c['status'],'changed':c['changed'],'pins':len(c['pins']),'arm_stub_test':c['arm_stub_test']}))
