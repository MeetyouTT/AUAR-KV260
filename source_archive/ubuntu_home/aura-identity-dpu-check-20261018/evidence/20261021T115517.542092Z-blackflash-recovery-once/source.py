"""One display-only reset, preserving framebuffer size and an independent restore timer."""
import fcntl,hashlib,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
BOOT='8817dc71-fe59-46fd-b235-83ffd93d56d1'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
env=dict(os.environ,DISPLAY=':0')
def cmd(args,timeout=6):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(args)+': '+p.stdout[-1200:])
 return p.stdout
def units():return cmd(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
def edid():
 b=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest() if b else None}
def scanout():
 s=Path('/sys/kernel/debug/dri/0/state').read_text()
 return [line.strip() for line in s.splitlines() if line.strip().startswith(('enable=','active=','mode:'))]
before=units();assert before.count('ActiveState=active')==3
pid=cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).strip()
argv=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0');config=Path(argv[argv.index('--config')+1])
assert hashlib.sha256(config.read_bytes()).hexdigest()=='1815ddb8c1eae71b511a46df0e28baafbaf19fdc877745b587079732b24e36c7'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:state=json.load(r)
assert state.get('phase')=='IDLE' and not state.get('playing') and not state.get('paused')
modes=cmd(['xrandr','--verbose']);assert 'DP-1 connected primary 1024x600+0+0' in modes
assert '49.000MHz -HSync -VSync' in modes and 'total  1312' in modes and 'total  624' in modes
root=Path('/home/root/aura-display-recovery-20261021')/BOOT
root.mkdir(parents=True,exist_ok=False)
lock=(root/'control.lock').open('xb');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
restore=root/'restore.py'
restore.write_text("import os,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r\ne=dict(os.environ,DISPLAY=':0')\nsubprocess.run(['xrandr','--fb','1024x600','--output','DP-1','--mode','1024x600','--rate','59.85','--primary','--pos','0x0'],env=e,check=True,timeout=8)\nsubprocess.run(['xset','dpms','force','on'],env=e,check=True,timeout=4)\n"%BOOT)
timer='aura-display-restore-'+str(os.getpid())
v={'boot_id':BOOT,'before_units':before,'before_edid':edid(),'before_scanout':scanout(),'off_succeeded':False,'off_scanout_verified':False,'restore_succeeded':False,'physical_panel_verified':False,'movement_commands_sent':0,'configuration_changed':False,'restore_file':str(restore),'timer':timer}
cmd(['systemd-run','--unit='+timer,'--on-active=15s','--timer-property=AccuracySec=1s','/usr/bin/python3','-B',str(restore)])
assert cmd(['systemctl','is-active',timer+'.timer']).strip()=='active'
try:
 try:
  v['off_output']=cmd(['xrandr','--fb','1024x600','--output','DP-1','--off'])
  v['off_succeeded']=True;v['off_scanout']=scanout();v['off_scanout_verified']='active=0' in v['off_scanout']
  assert v['off_scanout_verified'],'OFF command returned success but scanout remained active'
  started=time.monotonic();time.sleep(2);v['off_wait_seconds']=round(time.monotonic()-started,3)
 finally:
  v['restore_output']=cmd([sys.executable,'-B',str(restore)],timeout=14);v['restore_succeeded']=True
 after=cmd(['xrandr','--current']);assert 'DP-1 connected primary 1024x600+0+0' in after
 assert 'active=1' in scanout()
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 cmd(['systemctl','stop',timer+'.timer'])
 time.sleep(2);v.update(after_display=after,after_edid=edid(),after_scanout=scanout(),after_units=units())
 v['services_unchanged']=v['after_units']==before
 assert v['services_unchanged'],'Service state changed during display reset'
 v['status']='DISPLAY_RESET_VERIFIED_PHYSICAL_PENDING'
except Exception as e:v.update(status='RESET_INCOMPLETE_REVIEW_REQUIRED',error=str(e))
finally:
 (root/'result.json').write_text(json.dumps(v,indent=2)+'\n');lock.close()
print(json.dumps(v),flush=True)
