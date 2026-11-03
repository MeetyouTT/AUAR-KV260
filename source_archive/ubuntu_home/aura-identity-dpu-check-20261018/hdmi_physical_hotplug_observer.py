"""Observe one physical HDMI hotplug; no modeset or driver writes."""
import hashlib,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path

BOOT='975f931a-927b-4a06-b784-ebda8463177f'
ROOT=Path('/run/aura-hdmi-physical-hotplug-20261021')/BOOT

def cmd(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
 return {'rc':p.returncode,'text':p.stdout[-10000:]}

def cached():
 p=Path('/sys/class/drm/card0-DP-1');raw=(p/'edid').read_bytes()
 return {'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest(),
  'edid_valid':bool(raw and len(raw)%128==0 and raw[:8]==bytes.fromhex('00ffffffffffff00') and all(sum(raw[i:i+128])%256==0 for i in range(0,len(raw),128))),
  **{k:(p/k).read_text().strip() for k in ['status','enabled','dpms']}}

def snapshot():
 v={'uptime':Path('/proc/uptime').read_text().split()[0],'cached_before_query':cached()}
 v['xrandr']=cmd(['env','DISPLAY=:0','xrandr','--verbose'])
 v['cached_after_query']=cached()
 v['units']=cmd(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
 state=Path('/sys/kernel/debug/dri/0/state').read_text()
 v['scanout']=[s.strip() for s in state.splitlines() if re.search(r'format=|size=|pitch=|crtc-pos=|mode:|^\\s*enable=|^\\s*active=',s)]
 clock=Path('/sys/kernel/debug/clk/clk_summary').read_text()
 v['display_clocks']=[s.strip() for s in clock.splitlines() if re.search(r'\\b(?:dp_video_ref|dpdma_ref|dp_aclk)\\s',s)]
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for name,port,path,keys in [('gui',8783,'/api/state',['phase','playing','error','ui_page','avatar_display']),('camera',8790,'/health',['capture_frames','capture_hz','detection_hz','camera_error','detector_error'])]:
  try:
   with op.open('http://127.0.0.1:'+str(port)+path,timeout=2) as r:d=json.load(r)
   v[name]={k:d.get(k) for k in keys}
  except Exception as exc:v[name]={'unavailable':str(exc)}
 kernel=subprocess.check_output(['dmesg'],text=True)
 v['kernel_display']=[s for s in kernel.splitlines() if re.search(r'zynqmp-display|dpdma|aux.*(?:fail|error)|training|underflow|drm.*(?:edid|hotplug)',s,re.I)][-40:]
 return v

def observe():
 before=json.loads((ROOT/'before.json').read_text())
 samples=0;changes=[];last=None;longest=0;start=previous=time.monotonic()
 with (ROOT/'drm-events.txt').open('w') as log:
  monitor=subprocess.Popen(['udevadm','monitor','--kernel','--property','--subsystem-match=drm'],stdout=log,stderr=subprocess.STDOUT)
  try:
   time.sleep(.4)
   assert monitor.poll() is None,'DRM event monitor did not stay running'
   (ROOT/'state.json').write_text(json.dumps({'phase':'OBSERVING','boot_id':BOOT,'before':before})+'\n')
   while time.monotonic()-start<180 and not (ROOT/'finish').exists():
    now=time.monotonic();longest=max(longest,now-previous);previous=now
    value=cached();samples+=1
    if value!=last:
     changes.append({'elapsed':round(now-start,3),'state':value});last=value
     (ROOT/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
    time.sleep(.1)
  finally:
   monitor.terminate()
   try:monitor.wait(timeout=3)
   except subprocess.TimeoutExpired:monitor.kill();monitor.wait()
 after=snapshot()
 events=(ROOT/'drm-events.txt').read_text(errors='replace')
 result={'boot_id':BOOT,'before':before,'after':after,'cached_changes':changes,'samples':samples,'maximum_sampling_gap_seconds':round(longest,3),'finish_requested':(ROOT/'finish').exists(),
  'events':[s for s in events.splitlines() if re.search(r'^KERNEL|HOTPLUG=|CONNECTOR=|DEVNAME=|ACTION=|SEQNUM=',s)],'display_control_writes':0,'driver_rebinds':0,'reboots':0,'movement_commands_sent':0,'physical_result':'awaiting_user'}
 (ROOT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 (ROOT/'state.json').write_text(json.dumps({'phase':'COMPLETE','result_file':str(ROOT/'result.json')})+'\n')

def main(action):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert hashlib.sha256(Path('/etc/X11/xorg.conf').read_bytes()).hexdigest()=='64457c25a844ef95cd4ae62bacba80b0cbec5ae1a54efdc15e3ec02775c0555a'
 if action=='observe':observe()
 elif action=='finish':(ROOT/'finish').write_text('User has reported the physical test result; finish passive phase.\n');print(json.dumps({'finish_requested':True}))
 elif action=='status':
  result=ROOT/'result.json'
  print(result.read_text() if result.exists() else (ROOT/'state.json').read_text(),flush=True)
 else:
  assert action=='launch'
  ROOT.mkdir(parents=True,exist_ok=False)
  before=snapshot();(ROOT/'before.json').write_text(json.dumps(before,indent=2)+'\n')
  assert before['xrandr']['rc']==0 and before['gui'].get('phase')=='IDLE' and not before['gui'].get('playing')
  p=ROOT/'observer.py';p.write_bytes(Path(main.__code__.co_filename).read_bytes())
  launch=cmd(['systemd-run','--unit=aura-hdmi-hotplug-observer-'+BOOT[:8],'--property=RuntimeMaxSec=195','/usr/bin/python3','-B',str(p),'observe'])
  assert launch['rc']==0,launch
  deadline=time.monotonic()+4
  while time.monotonic()<deadline and not (ROOT/'state.json').exists():time.sleep(.1)
  assert (ROOT/'state.json').exists()
  print(json.dumps({'observer_ready':True,'root':str(ROOT),'before':before}),flush=True)

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'launch')
