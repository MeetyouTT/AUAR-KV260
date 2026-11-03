import hashlib,json,shutil,subprocess,sys
from pathlib import Path
B=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
OLD=B/'continuous-v12r1';NEW=B/'continuous-v12r2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
assert sha(OLD/'deployment-manifest.json')=='b307e8b19d2fd157286ce96e6b3eb867b01cb7002bbdda1050bb0f60e1b22923'
assert sha(NEW/'deployment-manifest.json')=='41a9df4e25c1ec7bfd75e6e3846e27cb4b94e727b6bdb1eba7c0398ffc8aa5f8'
old=json.loads((OLD/'deployment-manifest.json').read_text());new=json.loads((NEW/'deployment-manifest.json').read_text())
prior={str(Path(x['destination']).relative_to(OLD)):x for x in old['files']}
assert all(sha(x['destination'])==x['sha256'] for x in old['files'])
copied=[]
for row in new['files']:
 p=Path(row['destination']);rel=p.relative_to(NEW)
 if not p.exists():
  source=prior[str(rel)];assert source['sha256']==row['sha256']
  p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source['destination'],p);copied.append(str(rel))
 assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for name in ('continuous_session.py','continuous_face_control.py','run_face_motion.py'):
 compile((NEW/name).read_text(),name,'exec')
p=subprocess.run([sys.executable,'-B',str(B/'continuous-v12r2-verify/verify_board_pure.py')],capture_output=True,text=True,timeout=25)
assert p.returncode==0,(p.stdout,p.stderr)
result=json.loads(p.stdout);assert result['status']=='ARM_PURE_CONTROL_PASS'
print(json.dumps(dict(status='V12_PREPARED_NO_MOTION',runtime_files=len(new['files']),copied_unchanged=len(copied),board_software_verification=result,production_config_changed=False,motor_commands_sent=0),ensure_ascii=False))
