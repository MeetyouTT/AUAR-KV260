#!/usr/bin/env python3
"""Deploy and verify the explicitly owned full-screen camera preview."""
import base64, datetime, hashlib, importlib.util, json, shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ-fullscreen')
out.mkdir(parents=True)
spec=importlib.util.spec_from_file_location('uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
board='/home/root/aura-camera-check-20261006/fullscreen_preview.py'
guard="from pathlib import Path;assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';"
worker=(ROOT/'fullscreen_worker.py').read_bytes()
compile(worker,str(ROOT/'fullscreen_worker.py'),'exec')
with (out/'uart.raw').open('wb') as raw:
 u=mod.UART(raw)
 try:
  u.connect()
  def execute(code,marker):
   rc,data,sha=u.command('python3 -B -c '+shlex.quote(guard+code),marker,40)
   (out/(marker+'.txt')).write_bytes(data)
   if rc:raise RuntimeError(marker+': '+data.decode(errors='replace')[-1800:])
   return data
  execute("p=Path("+repr(board)+");p.parent.mkdir(exist_ok=True);p.with_suffix('.upload').write_bytes(b'')",'PREPARE')
  for i in range(0,len(worker),900):
   payload=base64.b64encode(worker[i:i+900]).decode()
   execute("import base64;p=Path("+repr(board)+").with_suffix('.upload');f=p.open('ab');f.write(base64.b64decode("+repr(payload)+"));f.close()",'CHUNK'+str(i//900))
  execute("import hashlib;p=Path("+repr(board)+");t=p.with_suffix('.upload');assert hashlib.sha256(t.read_bytes()).hexdigest()=="+repr(hashlib.sha256(worker).hexdigest())+";t.replace(p)",'VERIFY')
  launch=r'''
import os,signal,time,subprocess,json
root=Path('/home/root/aura-camera-check-20261006')
pf=root/'preview.pid'
old=int(pf.read_text()) if pf.exists() else 0
cp=Path('/proc')/str(old)/'cmdline'
if old and cp.exists():
 cmd=cp.read_bytes()
 assert (b'gst-launch-1.0' in cmd and b'device=/dev/video0' in cmd) or b'/home/root/aura-camera-check-20261006/fullscreen_preview.py' in cmd
 os.kill(old,signal.SIGTERM)
 for _ in range(30):
  if not cp.exists():break
  time.sleep(.1)
 assert not cp.exists(),'Previous camera process did not exit'
subprocess.run(['xset','-display',':0','dpms','force','on'],check=True)
sp=root/'fullscreen-status.json'
if sp.exists():sp.unlink()
log=(root/'fullscreen.log').open('ab',buffering=0)
p=subprocess.Popen(['python3','-u',str(root/'fullscreen_preview.py')],env=dict(os.environ,DISPLAY=':0'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
pf.write_text(str(p.pid))
time.sleep(4)
before=json.loads(sp.read_text()) if sp.exists() else {}
time.sleep(2)
after=json.loads(sp.read_text()) if sp.exists() else {}
print(json.dumps({'pid':p.pid,'running':p.poll() is None,'rc':p.poll(),'before':before,'after':after,'log':(root/'fullscreen.log').read_text()[-2400:]}))
'''
  result=json.loads(execute(launch,'LAUNCH'))
  (out/'result.json').write_text(json.dumps(result,indent=2))
  print(json.dumps({'evidence':str(out),'result':result},indent=2))
 finally:restored=u.close()
(ROOT/'CURRENT_FULLSCREEN.json').write_text(json.dumps({'evidence':str(out),'console_echo_restored':restored,'result':result},indent=2))
if not result['running'] or result['after'].get('frames',0)<=result['before'].get('frames',0):
 raise RuntimeError('Fullscreen preview did not produce advancing frames')
