"""Verify Python-only candidate on board; no service or hardware writes."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['board/identity/live.py','common/speaker_attribution.py','common/speaker_identity.py','common/speaker_validation.py','tools/check_motion_readiness.py',
       'config/servo_calibration.json','tests/framework/test_camera_identity.py','tests/framework/test_identity_face_targets.py',
       'tests/framework/test_speaker_identity.py']
sources={n:base64.b64encode((AURA/n).read_bytes()).decode() for n in names}
sources['tests/test_followup.py']=base64.b64encode((HERE/'test_followup.py').read_bytes()).decode()
script=r'''
import base64,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
files=FILES
root=Path('/home/root/aura-identity-motion-followup-20261021')/('candidate-'+str(time.monotonic_ns()))
active=Path('/home/root/aura-handsfree-dialogue-20261020/candidate-0c0a8ab46ec2/runtime/aura')
for source in active.rglob('*.py'):
 relative=source.relative_to(active)
 if any(p in ('models','.venv','submission') for p in relative.parts):continue
 target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for name,data in files.items():
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(data))
env=dict(os.environ,PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1')
rows=[]
for directory,pattern in [('tests/framework','test_camera_identity.py'),('tests/framework','test_identity_face_targets.py'),('tests/framework','test_speaker_identity.py'),('tests','test_followup.py')]:
 result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',directory,'-p',pattern],cwd=str(root),env=env,capture_output=True,text=True,timeout=45)
 rows.append({'pattern':pattern,'returncode':result.returncode,'output':result.stdout+result.stderr})
calibration=json.loads(Path('/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/runtime/aura/config/pan_manual.local.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
fdt=hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()
platform={'boot_id':boot,'configured_boot_id':calibration['boot_id'],'boot_matches':boot==calibration['boot_id'],
 'fdt_sha256':fdt,'fdt_matches':fdt==calibration['fdt_sha256'],
 'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()}
print(json.dumps({'candidate':str(root),'tests':rows,'platform':platform,'services_changed':False,'register_io':False}))
'''.replace('FILES',repr(sources))
value=json.loads(ssh('python3 -',script,timeout=150))
(HERE/'board_candidate_verification.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
