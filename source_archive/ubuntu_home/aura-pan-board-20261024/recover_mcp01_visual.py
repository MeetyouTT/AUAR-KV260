"""Finite MCP01-only recovery, with camera owner and motor STOP preserved."""
import fcntl,json,os,subprocess,time,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=O/'pan-face-edge-v3';GUI='aura-avatar-ui.service'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props():
 return dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','-p','Result','-p','ExecMainStatus'],text=True).splitlines() if '=' in x)
def pressure():
 fd=os.open('/dev/kmsg',os.O_RDONLY|os.O_NONBLOCK);count=0;overruns=0;start=time.monotonic()
 try:
  os.lseek(fd,0,os.SEEK_END)
  while time.monotonic()-start<.3 and count<20000:
   try:
    r=os.read(fd,8192)
    if b"couldn't access mem fast enough" in r:count+=1
   except BlockingIOError:time.sleep(.002)
   except OSError:overruns+=1
 finally:os.close(fd)
 return {'warnings':count,'seconds':round(time.monotonic()-start,3),'reader_overruns':overruns}
lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
b=get(8790,'/health');u=get(8783,'/api/state');p=u['manual_pan'];r=p['readback']
assert u['phase']=='IDLE' and not u.get('playing') and u['audio_output_state']=='IDLE_READY'
assert p['state']=='READY' and r['flags']==0 and r['lease_left_ms']==0
device=Path('/sys/bus/usb/devices/1-1.2');assert (device/'idVendor').read_text().strip()=='17ef' and (device/'idProduct').read_text().strip()=='a03b'
report={'camera_before':b['pid'],'warnings_before':pressure(),'usb_reset':False};stopped=False
try:
 subprocess.run(['systemctl','stop','--no-block',GUI],check=True);stopped=True;end=time.monotonic()+25
 while time.monotonic()<end and props()['MainPID']!='0':time.sleep(.2)
 assert props()['MainPID']=='0' and props()['Result']=='success' and props()['ExecMainStatus']=='0'
 report['warnings_audio_closed']=pressure()
 bus=int((device/'busnum').read_text());num=int((device/'devnum').read_text());node='/dev/bus/usb/%03d/%03d'%(bus,num)
 fd=os.open(node,os.O_WRONLY)
 try:fcntl.ioctl(fd,0x5514,0);report['usb_reset']=True
 finally:os.close(fd)
 time.sleep(.5);report['warnings_after_reset']=pressure()
finally:
 if stopped:subprocess.run(['systemctl','start','--no-block',GUI],check=True)
 end=time.monotonic()+100;final=None
 while time.monotonic()<end:
  try:
   v=get(8783,'/api/state')
   if v['phase']=='IDLE' and v['manual_pan']['state']=='READY':final=v;break
  except Exception:pass
  time.sleep(.5)
 report['gui_unit']=props();report['manual_restored']=final is not None
 if final and final['manual_pan']['left_sign']==-1:
  base='http://127.0.0.1:8783';req=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_reverse"}',headers={'Origin':base,'Content-Type':'application/json'})
  with o.open(req,timeout=3) as reply:assert json.load(reply)['ok']
 report['warnings_after_gui']=pressure();a=get(8790,'/health')
 report.update(camera_after=a['pid'],camera_unchanged=a['pid']==b['pid'],primary_delta=a['dpu_schedule']['primary_period_overruns']-b['dpu_schedule']['primary_period_overruns'],
  optional_delta={k:a['dpu_schedule']['optional'][k]['overruns']-b['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')})
 s=json.loads((F/'stage-state.json').read_text());s['gui_pid']=int(report['gui_unit']['MainPID']);(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n')
 print(json.dumps(report,sort_keys=True))
