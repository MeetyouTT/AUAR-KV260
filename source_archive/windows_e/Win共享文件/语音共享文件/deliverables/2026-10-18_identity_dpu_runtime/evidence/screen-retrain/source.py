"""Reapply the existing verified output timing with an independent restore."""
import hashlib,json,os,re,subprocess,time
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
env=dict(os.environ,DISPLAY=':0')
def run(args,timeout=5):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(args)+': '+p.stdout[-500:])
 return p.stdout
def display_edid():
 raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
 return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest() if raw else None}
before=run(['xrandr','--verbose'])
assert 'DP-1 connected primary 1024x600+0+0' in before
patterns=[r'1024x600\s+\([^\n]+\)\s+49\.000MHz\s+-HSync\s+-VSync',r'h: width\s+1024 start\s+1072 end\s+1168 total\s+1312',r'v: height\s+600 start\s+603 end\s+613 total\s+624']
assert all(re.search(pattern,before) for pattern in patterns)
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
restore=root/('display-restore-'+str(os.getpid())+'.py')
restore.write_text("import os,subprocess\ne=dict(os.environ,DISPLAY=':0')\nsubprocess.run(['xrandr','--output','DP-1','--mode','1024x600','--rate','59.85'],env=e,timeout=7,check=True)\nsubprocess.run(['xset','dpms','force','on'],env=e,timeout=5,check=True)\n")
timer='aura-display-recover-'+str(os.getpid())
run(['systemd-run','--unit='+timer,'--on-active=12s','/usr/bin/python3','-B',str(restore)])
report={'status':'DISPLAY_RETRAIN_STARTED','boot_id':boot,'before_edid':display_edid(),'physical_panel_verified':False}
try:
 try:
  run(['xrandr','--output','DP-1','--off']);time.sleep(1)
 finally:
  run(['python3','-B',str(restore)],13)
 after=run(['xrandr','--current'])
 assert 'DP-1 connected primary 1024x600+0+0' in after
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 run(['systemctl','stop',timer+'.timer'])
 report.update(status='PASS_SOFTWARE_MODE_RESET_PHYSICAL_PENDING',display_after=after,after_edid=display_edid())
except Exception as exc:report.update(status='DISPLAY_RESET_FAILED_RESTORE_TIMER_RETAINED',error=str(exc))
(root/('display-retrain-'+str(os.getpid())+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
