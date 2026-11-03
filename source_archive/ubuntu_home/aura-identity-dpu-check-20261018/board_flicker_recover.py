"""Restore the familiar page and retrain the verified live display, once."""
import hashlib,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='33d0dc5b-27f4-4060-ae25-d2e8e8ddabc3'
env=dict(os.environ,DISPLAY=':0')
def cmd(args,timeout=6):return subprocess.check_output(args,env=env,stderr=subprocess.STDOUT,text=True,timeout=timeout)
def unit(name):return cmd(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts'])
def api(data=None):
 base='http://127.0.0.1:8783';req=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=3) as response:return json.load(response)
raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='727d3e1893df759c757c35232f9465b670a64d6de2011b586de48c6446e17c35'
modes=cmd(['xrandr','--current','--verbose'])
assert 'DP-1 connected primary 1024x600+0+0' in modes
assert '49.000MHz -HSync -VSync' in modes and 'total  1312' in modes and 'total  624' in modes
before={name:unit(name) for name in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']}
state=api();assert state['phase']=='IDLE' and not state['playing'] and not state['paused']
root=Path('/home/root/aura-display-flicker-20261020')/('recovery-'+str(os.getpid()));root.mkdir(parents=True,exist_ok=False)
restore=root/'restore.py'
restore.write_text("import os,subprocess\ne=dict(os.environ,DISPLAY=':0')\nsubprocess.run(['xrandr','--output','DP-1','--mode','1024x600','--rate','59.85'],env=e,check=True,timeout=7)\nsubprocess.run(['xset','dpms','force','on'],env=e,check=True,timeout=4)\n")
timer='aura-flicker-restore-'+str(os.getpid())
cmd(['systemd-run','--unit='+timer,'--on-active=12s','/usr/bin/python3','-B',str(restore)])
v={'boot_id':boot,'before':before,'ui_before':{k:state.get(k) for k in ['phase','ui_page','ui_layer']},'physical_panel_verified':False,'movement_commands_sent':0,'backup_restore':str(restore),'off_succeeded':False,'restore_succeeded':False}
try:
 try:
  cmd(['xrandr','--output','DP-1','--off']);v['off_succeeded']=True;time.sleep(2)
 finally:
  cmd([sys.executable,'-B',str(restore)],timeout=12);v['restore_succeeded']=True
 assert 'DP-1 connected primary 1024x600+0+0' in cmd(['xrandr','--current'])
 cmd(['systemctl','stop',timer+'.timer'])
 result=api({'type':'ui_page','page':'main'});assert result.get('ok'),result
 deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  state=api()
  if state.get('ui_page')=='main' and state.get('ui_layer')=='presentation':break
  time.sleep(.1)
 else:raise RuntimeError('Main page readback did not settle')
 v['after']={name:unit(name) for name in before};assert v['after']==before
 v['ui_after']={k:state.get(k) for k in ['phase','ui_page','ui_layer','error']}
 v['status']='OUTPUT_REBUILT_MAIN_RESTORED_PHYSICAL_PENDING'
except Exception as exc:v.update(status='RECOVERY_INCOMPLETE_REVIEW_REQUIRED',error=str(exc))
(root/'result.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
