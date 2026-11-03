"""Load the already installed paired joint firmware while both owners are stopped."""
import fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');APP='aura-visual-servo-b4096-v2'
def command(a,t=20):
 p=subprocess.run(a,capture_output=True,text=True,timeout=t)
 assert p.returncode==0,p.stderr[-400:]
 return p.stdout
def props(n):
 x=command(['systemctl','show',n,'-p','MainPID','-p','Result','-p','ExecMainStatus'])
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
def active():
 return [v[0] for v in (x.split() for x in command(['xmutil','listapps']).splitlines()) if len(v)==6 and v[1] in ('XRT_FLAT','PL_FLAT') and v[-1].rstrip(',')=='0']
s=json.loads((R/'state.json').read_text());assert s['phase']=='CAMERA_STOPPED_CHECKPOINT_PASS' and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert hashlib.sha256(Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/startup/config.json').read_bytes()).hexdigest()=='d12af30e70b75be8fd54d6d030e3b98a9df204bacb803fbf6fc5914e9f391594'
lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert props('aura-camera-ui.service')['MainPID']=='0'
g=props('aura-avatar-ui.service');assert g['MainPID']==str(s['gui_pid'])
command(['systemctl','stop','--no-block','aura-avatar-ui.service']);end=time.monotonic()+40
while time.monotonic()<end:
 if props('aura-avatar-ui.service')['MainPID']=='0':break
 time.sleep(.2)
assert props('aura-avatar-ui.service')['MainPID']=='0'
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for rows in s['units'].values() for p,v in rows.items())
old=Path(s['old_root']);manifest=json.loads((old/'candidate-manifest.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in manifest['runtime_files'].items())
with Path('/run/aura-person-dpu.lock').open('a+') as dpu,Path('/run/aura-vsrv.lock').open('a+') as motion:
 fcntl.flock(dpu,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(motion,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert Path('/sys/module/zocl/refcnt').read_text().strip()=='0' and active()==['kv260-benchmark-b4096']
 command(['xmutil','unloadapp'],45);assert active()==[]
 command(['xmutil','loadapp',APP],60);assert active()==[APP]
 assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
 assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==APP+'.bit.bin'
 assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/'+APP+'/'+APP+'.xclbin\n'
assert hashlib.sha256((old/'bench_identity_stop.py').read_bytes()).hexdigest()=='ce2c6cb9d0b843f6edb6f56e2a8327bf1c76cdbb9acaf21aaf0962b67af571b6'
args=['/usr/bin/python3','-B',str(old/'bench_identity_stop.py'),'--execute','--confirmation','ID_STOP_ONLY','--manifest',str(old/'candidate-manifest.json'),'--manifest-sha256','ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab','--context',str(R/'context.json'),'--output',str(R/'id-stop.json')]
command(args,20);proof=json.loads((R/'id-stop.json').read_text());assert proof['identity_stop_passed']
s.update(phase='JOINT_FIRMWARE_ID_STOP_PASS',active_app=APP,id_stop_passed=True)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'after_stop':proof['after_stop'],'ARM_sent':False,'COMMIT_sent':False}))
