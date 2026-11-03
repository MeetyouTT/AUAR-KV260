"""Activate the fresh bounded GUI config, leaving the native camera running."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');GUI='aura-avatar-ui.service';OLDGUI=Path('/home/root/aura-pan-ui-v2-20261024/observed-ecfbdef064d157b6')
DROP=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzzzz-aura-pan-current-463c.conf')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def pid(n):return subprocess.check_output(['systemctl','show',n,'-p','MainPID','--value'],text=True).strip()
s=json.loads((R/'state.json').read_text());assert s['phase']=='MANUAL_UI_PREPARED_HUMAN_CONFIRMED';G=Path(s['gui_release'])
assert sha(G/'startup/config.json')==s['startup_config_sha256'] and sha(G/'manual-release/release.json')==s['manual_release_sha256'] and not DROP.exists()
h=get(8790,'/health');u=get(8783,'/api/state');assert h['pid']==s['current_camera_pid'] and not h['dpu_schedule']['owner_fenced']
assert pid(GUI)==str(s['gui_pid']) and u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
subprocess.run(['systemctl','stop','--no-block',GUI],check=True);end=time.monotonic()+40
while time.monotonic()<end:
 if pid(GUI)=='0':break
 time.sleep(.2)
assert pid(GUI)=='0'
old=json.loads((OLDGUI/'startup/config.json').read_text())['runtime']
for p in Path(old).glob('*settings*.json'):
 if p.is_file():shutil.copy2(p,G/'runtime'/p.name)
raw=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(G/'startup/launcher.py')+' --config '+str(G/'startup/config.json')+'\nWorkingDirectory='+str(G/'runtime/aura')+'\n').encode()
with DROP.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
try:
 subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','reset-failed',GUI],check=True);subprocess.run(['systemctl','start','--no-block',GUI],check=True)
 end=time.monotonic()+210;ready=None
 while time.monotonic()<end:
  try:
   q=get(8783,'/api/state');m=q.get('manual_pan',{});r=m.get('readback',{})
   if q['phase']=='IDLE' and m.get('state')=='READY' and r.get('flags')==0 and r.get('lease_left_ms')==0:ready=q;break
  except Exception:pass
  time.sleep(.5)
 assert ready is not None,'GUI readiness hold'
 assert get(8790,'/health')['pid']==s['current_camera_pid']
 assert sha(s['database_path'])==s['database_sha256']
 s.update(phase='CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED',current_gui_pid=int(pid(GUI)),gui_dropin=str(DROP),gui_dropin_sha256=sha(DROP))
 (R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
 print(json.dumps({'phase':s['phase'],'camera_pid':s['current_camera_pid'],'gui_pid':s['current_gui_pid'],'manual':ready['manual_pan'],'automatic_following':False,'new_movement_commands_sent':0},ensure_ascii=False))
except BaseException:
 if DROP.is_file() and sha(DROP)==hashlib.sha256(raw).hexdigest() and pid(GUI)=='0':
  DROP.unlink();subprocess.run(['systemctl','daemon-reload']);subprocess.run(['systemctl','start','--no-block',GUI])
 raise
