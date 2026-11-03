"""One bounded display-only driver reprobe with an independent recovery timer."""
import hashlib,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path

BOOT='975f931a-927b-4a06-b784-ebda8463177f'
CID='0353445345333247805558c00401a100'
ROOT=Path('/home/root/aura-display-reprobe-20261021')/BOOT/'once'
DEVICE=Path('/sys/bus/platform/devices/fd4a0000.display')
DRIVER=Path('/sys/bus/platform/drivers/zynqmp-display')
UNITS=['aura-avatar-ui.service','xserver-nodm.service']
PROTECTED={
 '/boot/uEnv.txt':'d120b2f78e40ec690fcda92f5c0791a93d587cf75d399695301005c45800d369',
 '/etc/X11/xorg.conf':'64457c25a844ef95cd4ae62bacba80b0cbec5ae1a54efdc15e3ec02775c0555a',
 '/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/startup/launcher.py':'cd1680220b60f6120db1bc847ca59cfd445796ff37e48a3ba93efca65eddfd98',
 '/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/startup/config.json':'3721a1f6101a4e14f88cab7f66e4430886206a55b21fafa33c56acf56c9395a0',
}

def run(args,timeout=8,check=True):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError('Command failed: '+repr(args)+': '+p.stdout[-1500:])
 return p.stdout

def pid(unit):
 return int(run(['systemctl','show',unit,'-p','MainPID','--value']).strip())

def api(port,path,keys):
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=2) as r:d=json.load(r)
 return {k:d.get(k) for k in keys}

def guards():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()==CID
 for name,sha in PROTECTED.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,name
 assert Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip()=='N'
 assert Path('/sys/class/drm/renderD128/device/driver').resolve().name=='zocl-drm','DPU owner is not isolated'

def preflight():
 guards()
 assert (DEVICE/'driver').resolve()==DRIVER
 assert Path('/sys/class/drm/card0/device').resolve()==DEVICE.resolve()
 assert (DRIVER/'bind').exists() and (DRIVER/'unbind').exists()
 assert pid('aura-camera-ui.service')==1014
 assert pid('aura-avatar-ui.service')==1075 and pid('xserver-nodm.service')==1074
 ui=api(8783,'/api/state',['phase','playing','error'])
 assert ui['phase']=='IDLE' and not ui['playing'],'Application busy'
 assert not Path('/sys/class/drm/card0-DP-1/edid').read_bytes(),'EDID already recovered; inspect before any reset'
 return {'boot_id':BOOT,'gui':ui,'camera_pid':1014,'display_driver':str(DRIVER),'dpu_driver':'zocl-drm','source_configuration_verified':True,'driver_writes':0}

def state(phase,**values):
 p=ROOT/'state.json'
 data={'boot_id':BOOT,'phase':phase,'uptime':Path('/proc/uptime').read_text().split()[0],**values}
 temp=ROOT/'state.tmp';temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,p)

def ensure_display_and_units():
 guards()
 if not (DEVICE/'driver').exists():
  (DRIVER/'bind').write_text(DEVICE.name)
 assert (DEVICE/'driver').resolve()==DRIVER
 run(['systemctl','start','--no-block',*reversed(UNITS)])

def display_owners():
 owners=[]
 for p in Path('/proc').glob('[0-9]*/fd/*'):
  try:
   if str(p.resolve())=='/dev/dri/card0':owners.append(str(p))
  except OSError:pass
 return owners

def worker():
 result={'boot_id':BOOT,'driver_unbind_sent':False,'driver_bind_sent':False,'system_reboots':0,'movement_commands_sent':0,'physical_fix_verified':False}
 try:
  preflight();state('STOPPING_GUI')
  run(['systemctl','stop',UNITS[0]],timeout=20)
  state('STOPPING_XSERVER');run(['systemctl','stop',UNITS[1]],timeout=20)
  assert pid('aura-avatar-ui.service')==0 and pid('xserver-nodm.service')==0
  assert pid('aura-camera-ui.service')==1014
  assert not display_owners(),'Another process still owns the display'
  guards();state('REMOVING_DISPLAY_DRIVER')
  (DRIVER/'unbind').write_text(DEVICE.name);result['driver_unbind_sent']=True
  assert not (DEVICE/'driver').exists()
  assert not Path('/sys/class/drm/card0').exists(),'Display DRM device remained after removal'
  start=time.monotonic();state('DISPLAY_DRIVER_REMOVED_WAITING_5S')
  time.sleep(5);result['driver_off_seconds']=round(time.monotonic()-start,3)
  state('REBINDING_DISPLAY_DRIVER');(DRIVER/'bind').write_text(DEVICE.name);result['driver_bind_sent']=True
  assert (DEVICE/'driver').resolve()==DRIVER
  state('STARTING_EXISTING_SERVICES');ensure_display_and_units()
  deadline=time.monotonic()+65
  while time.monotonic()<deadline:
   try:
    ui=api(8783,'/api/state',['phase','playing','ui_page','error','avatar_display'])
    cam=api(8790,'/health',['capture_frames','capture_hz','detection_hz','camera_error','detector_error'])
    units=run(['systemctl','show',*UNITS,'aura-camera-ui.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
    if units.count('ActiveState=active')==3 and not ui.get('error') and not cam.get('camera_error') and not cam.get('detector_error'):break
   except Exception:pass
   time.sleep(1)
  else:raise RuntimeError('Display/UI readiness deadline exceeded')
  raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
  result.update(edid_bytes=len(raw),edid_sha256=hashlib.sha256(raw).hexdigest(),gui=ui,camera=cam,units=units)
  result['display']=run(['env','DISPLAY=:0','xrandr','--verbose'])
  assert '49.000MHz -HSync -VSync *current' in result['display']
  assert pid('aura-camera-ui.service')==1014
  guards()
  result['source_configuration_unchanged']=True
  result['software_recovery_complete']=True
  result['watchdog_cancel']=run(['systemctl','stop','aura-display-recover-'+BOOT[:8]+'.timer'])
  (ROOT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  state('COMPLETE',edid_bytes=result['edid_bytes'],result_file=str(ROOT/'result.json'))
 except BaseException as exc:
  result['error']=str(exc)
  try:ensure_display_and_units();result['recovery_start_requested']=True
  except BaseException as recovery:result['recovery_error']=str(recovery)
  (ROOT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  state('FAILED_RECOVERY_REQUESTED',error=str(exc),result_file=str(ROOT/'result.json'))
  raise

def main(action):
 assert action in ['preflight','launch','worker','restore']
 if action=='preflight':print(json.dumps(preflight()),flush=True)
 elif action=='restore':
  ensure_display_and_units()
  (ROOT/'independent-recovery.json').write_text(json.dumps({'boot_id':BOOT,'recovery_requested':True})+'\n')
 elif action=='worker':worker()
 else:
  before=preflight();ROOT.mkdir(parents=True,exist_ok=False)
  (ROOT/'before.json').write_text(json.dumps(before,indent=2)+'\n')
  source=ROOT/'control.py';source.write_bytes(Path(main.__code__.co_filename).read_bytes())
  timer='aura-display-recover-'+BOOT[:8]
  run(['systemd-run','--unit='+timer,'--on-active=60','--property=RuntimeMaxSec=20','/usr/bin/python3','-B',str(source),'restore'])
  assert run(['systemctl','is-active',timer+'.timer']).strip()=='active'
  state('LAUNCHING_WORKER')
  try:
   launch=run(['systemd-run','--unit=aura-display-reprobe-'+BOOT[:8],'--property=RuntimeMaxSec=100','/usr/bin/python3','-B',str(source),'worker'])
  except BaseException:
   run(['systemctl','stop',timer+'.timer'],check=False);raise
  print(json.dumps({'root':str(ROOT),'worker_requested':True,'recovery_timer_armed':True,'launch':launch}),flush=True)

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'preflight')
