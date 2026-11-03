import os,json,hashlib,subprocess,re
from pathlib import Path
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
dev=os.stat('/').st_dev
assert Path('/sys/dev/block/%d:%d'%(os.major(dev),os.minor(dev))).resolve().name=='mmcblk1p2'
mod=Path('/sys/module/zocl')
assert (mod/'srcversion').read_text().strip()=='0991D1B457855C8987936E6'
params={p.name:p.read_text().strip() for p in (mod/'parameters').iterdir()}
assert params=={'enable_xgq_ert':'1'}
active=[]
text=subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True)
for line in text.splitlines():
 f=line.split()
 if f and re.fullmatch(r'-?\d+,?',f[-1]) and int(f[-1].rstrip(','))!=-1:active.append([f[0],int(f[-1].rstrip(','))])
assert active==[['kv260-benchmark-b4096',0]],'Unexpected active apps'
pid=int(subprocess.check_output(['systemctl','show','dfx-mgr.service','--property=MainPID','--value'],text=True))
assert pid>0
clients=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  for fd in (proc/'fd').iterdir():
   try:t=os.readlink(fd)
   except OSError:continue
   if t.startswith('/dev/dri/'):clients.append({'pid':int(proc.name),'comm':(proc/'comm').read_text().strip(),'fd':fd.name,'target':t})
 except OSError:continue
paths=['/usr/bin/dfx-mgrd','/usr/bin/dfx-mgr-client','/usr/lib/libdfx.so.1.0','/lib/libc.so.6','/lib/libpthread.so.0','/lib/ld-linux-aarch64.so.1','/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko','/etc/vart.conf','/etc/dfx-mgrd/daemon.conf']
files={p:{'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths}
cfg={p:Path(p).read_text() if Path(p).is_file() else None for p in ['/etc/dfx-mgrd/daemon.conf','/etc/dfx-mgrd/default_firmware']}
units=subprocess.check_output(['systemctl','show','dfx-mgr.service','--property=FragmentPath,DropInPaths,ExecStart,ExecStartPre'],text=True)
fdinfo={p.name:p.read_text() for p in (Path('/proc')/str(pid)/'fdinfo').iterdir() if 'inotify wd:' in p.read_text()}
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().strip(),'active':active,'driver_params':params,'files':files,'config':cfg,'service':units,'daemon_pid':pid,'daemon_exe':os.readlink('/proc/%d/exe'%pid),'fdinfo':fdinfo,'drm_clients':clients,'zocl_refcnt':(mod/'refcnt').read_text().strip(),'holders':[p.name for p in (mod/'holders').iterdir()]},indent=2),flush=True)

assert not clients,'DRM clients present'
assert (mod/'refcnt').read_text().strip()=='0' and not list((mod/'holders').iterdir())
assert os.readlink('/proc/%d/exe'%pid)=='/usr/bin/dfx-mgrd'
assert not subprocess.check_output(['systemctl','show','dfx-mgr.service','--property=DropInPaths','--value'],text=True).strip()
