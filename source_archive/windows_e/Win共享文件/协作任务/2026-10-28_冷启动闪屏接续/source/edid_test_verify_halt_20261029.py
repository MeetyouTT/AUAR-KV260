"""Require a fresh quiescent checkpoint, then schedule the requested normal shutdown."""
import ast,fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
BOOT='e004cfbf-fdde-433d-b372-c8e420db2699'
ROOT=Path('/home/root/aura-hdmi-resume-20261029')/BOOT
CFG='/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/board_camera_ui.proposed.json'
policy=Path('/home/root/aura-post-power-20261022/helpers/71eed27c50dd12b9/source.py')
raw=policy.read_bytes();assert hashlib.sha256(raw).hexdigest()=='71eed27c50dd12b921ce4fe5ff4b9facb8151d9dee6376df48da254beb7fc55c'
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='validate_checkpoint'];assert len(nodes)==1
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(policy),'exec'))
def props(unit):
    s=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','Result','-p','ExecMainStatus'],text=True,timeout=3)
    return dict(v.split('=',1) for v in s.splitlines() if '=' in v)
def save(name,value):
    with (ROOT/name).open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
lock=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
b=json.loads((ROOT/'before.json').read_text());assert (b['boot_id'],b['pid'],b['birth'])==(BOOT,28782,144580)
assert json.loads((ROOT/'stopped.json').read_text())['boot_id']==BOOT
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in b['pins'].items())
gui=props('aura-avatar-ui.service');assert gui=={'MainPID':'0','Result':'success','ExecMainStatus':'0'}
cp=Path(json.loads(Path(CFG).read_text())['native_execution']['checkpoint_output']);assert not cp.is_symlink()
doc=json.loads(cp.read_text());alive=Path('/proc/28782/stat').exists()
if alive:alive=int(Path('/proc/28782/stat').read_text().rsplit(')',1)[1].split()[19])==144580
free=False
with open('/run/aura-person-dpu.lock','a+') as f:
    try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
    except BlockingIOError:pass
validate_checkpoint(doc,b,BOOT,28782,144580,props('aura-camera-ui.service'),alive,free)
handoff=b['dpu_schedule']['protection_handoff']
assert handoff['native_abi_compatible_migration'] is True
assert doc['source_unit_sha256']==handoff['native_unit_sha256']
assert hashlib.sha256(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/identity_recovery.py').read_bytes()).hexdigest()=='64831498d8497c2087b3bb1543367e8cc1917ca131694000884f2d58e60990f7'
assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0'
save('checkpoint.json',doc)
d={'source_boot':BOOT,'normal_stop_verified':True,'checkpoint_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'checkpoint_path':str(cp),'dpu_lock_free':free,'zocl_refcnt':0,'history_not_decreased':True}
save('verified.json',d);os.sync()
subprocess.run(['systemd-run','--quiet','--unit=aura-hdmi-cold-poweroff-e004cfbf-20261029','--on-active=12s','/bin/systemctl','poweroff','--no-block'],check=True,timeout=4)
d.update(poweroff_scheduled=True,delay_seconds=12,next='Wait for observed Power down before disconnecting board 12V; retain HDMI and screen USB')
print(json.dumps(d))
