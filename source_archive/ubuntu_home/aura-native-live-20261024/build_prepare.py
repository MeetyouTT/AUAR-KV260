"""Seal controller sources/metadata; no model bytes or service actions here."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

root=Path(__file__).resolve().parent
previous=root.parent/'aura-native-critical-20261024'
inventory=json.loads((root/'inventory.private.json').read_text())
files={}
for name in ['policy.py','boot_ops.py','native_entry.py','rollback_entry.py']:
    raw=(root/name).read_bytes();ast.parse(raw);files[name]=base64.b64encode(raw).decode()
for name in ['equivalence_benchmark.py','build_plan.py']:
    raw=(previous/'equivalence-benchmark'/name).read_bytes();ast.parse(raw);files[name]=base64.b64encode(raw).decode()
yolo={k:v for k,v in inventory['yolo_config'].items() if k not in ('reference_image','reference_sha256')}
models=[]
for task,key in [('yunet','face_backend'),('sface','feature_backend')]:
    cfg=inventory['face_backends'][key]
    models.append({'task':task,'model':cfg['model'],'manifest':cfg['manifest'],
                   'source_ttl_ns':1_000_000_000})
for name,value in [('yolo.json',yolo),('models.json',models)]:
    files[name]=base64.b64encode((json.dumps(value,indent=2)+'\n').encode()).decode()
baseline=json.loads((previous/'actual-production-python-manifest.json').read_text())
payload=json.dumps({'files':files,'legacy_python':baseline['files']},sort_keys=True,separators=(',',':')).encode()
body='''import base64,gzip,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
source=Path(sys._getframe().f_code.co_filename).resolve();token=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
root=Path('/home/root/aura-native-live-20261024/ops')/token;root.mkdir(parents=True,exist_ok=False,mode=0o700)
data=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(data).hexdigest()==PAYLOAD_SHA
value=json.loads(data);pins={}
for name,encoded in value['files'].items():
 p=root/name;assert p.parent==root
 raw=base64.b64decode(encoded)
 with p.open('xb') as out:out.write(raw)
 pins[name]=hashlib.sha256(raw).hexdigest()
legacy=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb')
candidate=Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
protected={str(legacy/'aura'/name):pin for name,pin in value['legacy_python'].items()}
for name,pin in protected.items():assert sha(name)==pin
camera_unit=Path('/etc/systemd/system/aura-camera-ui.service')
assert sha(camera_unit)=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
extra=[camera_unit,Path('/etc/systemd/system/aura-avatar-ui.service'),
 Path('/etc/systemd/system/aura-camera-ui.service.d/zzzz-aura-vision-recovery-c76110abefc304bb.conf'),
 legacy/'runtime_entry.py',legacy/'gil_camera_launcher.py',legacy/'board_camera_ui.json',
 candidate/'camera-python-manifest.json',candidate/'board_camera_ui.proposed.json']
for p in extra:protected[str(p)]=sha(p)
assert sha(candidate/'board_camera_ui.proposed.json')=='96948ff14f2e720963c16f12391e50a11281d4a04dc6b05e7f3fd15244a6b9e7'
manifest=json.loads((candidate/'camera-python-manifest.json').read_text())['files']
for name,pin in manifest.items():
 p=candidate/'aura'/name;assert sha(p)==pin;protected[str(p)]=pin
library=Path('/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/libaura_native_v2_candidate.so')
assert sha(library)=='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656';protected[str(library)]=sha(library)
prefix=Path('/home/root/aura-native-critical-20261024/legacy-prefix/ecda1d52dbc4d3a0/legacy-boot-archive.json')
protected[str(prefix)]=sha(prefix)
meta={'root':str(root),'tag':token,'source_boot':'008f3e1b-c627-4b98-b120-d2a460cdbcbe',
 'old_camera_pid':29563,'old_gui_pid':29588,'legacy_root':str(legacy),'candidate_root':str(candidate),
 'candidate_config':str(candidate/'board_camera_ui.proposed.json'),
 'candidate_ui_sha256':manifest['board/vision/ui_camera_service.py'],
 'native_library':str(library),'prefix_path':str(prefix),'source_pins':pins,'protected':protected}
with (root/'meta.json').open('x') as out:json.dump(meta,out,indent=2)
with (root/'state.json').open('x') as out:json.dump({'phase':'PREPARED','owned':{},'maintenance_started':False},out)
run=subprocess.run(['/usr/bin/python3','-B',str(root/'boot_ops.py'),'--root',str(root),'status'],capture_output=True,text=True,timeout=5)
assert run.returncode==0,run.stderr
print(json.dumps({'scope':'PREPARED_ONLY_NO_UNIT_INSTALL_NO_REBOOT_NO_MODEL',
 'root':str(root),'tag':token,'source_pins':pins,'status':json.loads(run.stdout),
 'protected_files':len(protected),'models_loaded':False,'services_changed':False}))
'''
output=root/'board_prepare.py'
output.write_text('PAYLOAD='+repr(base64.b64encode(gzip.compress(payload,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(payload).hexdigest())+'\n'+body)
ast.parse(output.read_text());assert output.stat().st_size<300000
print(json.dumps({'helper':str(output),'bytes':output.stat().st_size,'source_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
