"""Apply the user's ten-percent left boundary and replace only its overlay."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');p=R/'face-zone-settings.json'
source=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/zone-editor-v5/face_zone_editor.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='c35b328e62e93b4c9f2b852a1cbdd58a1805bd2cdcd2e126e1b92ea4084ce5a9'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as response:u=json.load(response)
m=u['manual_pan'];assert not m['automatic_following'] and m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
gui=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
camera=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
unit='aura-face-zone-editor.service';before=json.loads(p.read_text())
subprocess.run(['systemctl','stop',unit],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
assert json.loads(p.read_text())==before
backup=R/'left-line-ten-percent-before.json'
with backup.open('x') as f:json.dump(before,f,indent=2);f.write('\n')
after=dict(before,left_camera_ratio=.1,updated_mono_ms=int(time.monotonic()*1000))
temp=p.with_name(p.name+'.left-ten-percent');assert not temp.exists();temp.write_text(json.dumps(after,indent=2)+'\n');os.chmod(temp,0o600);os.replace(temp,p)
subprocess.run(['systemd-run','--quiet','--collect','--unit=aura-face-zone-editor','--property=Restart=no','/usr/bin/python3','-B',str(source),'--settings',str(p)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
time.sleep(1.5);current=json.loads(p.read_text())
assert current['left_camera_ratio']==.1 and current['right_ratio']==before['right_ratio'] and current['left_ratio']==0.
assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()==gui
assert subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()==camera
print(json.dumps({'status':'VISIBLE_LEFT_BOUNDARY_TEN_PERCENT_INSTALLED','settings':current,'screen_left_x':132,
 'screen_right_x':8+current['right_ratio']*568,'gui_pid':int(gui),'camera_pid':int(camera),
 'editor_pid':int(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True)),
 'camera_restarted':False,'gui_restarted':False,'motor_commands':0}))
