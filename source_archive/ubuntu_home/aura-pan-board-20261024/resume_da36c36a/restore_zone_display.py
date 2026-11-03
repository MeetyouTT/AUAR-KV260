import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');OLD=Path('/home/root/aura-pan-current-20261024/16a07283/face-zone-settings.json')
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/zone-editor-v8/face_zone_editor.py')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
assert hashlib.sha256(P.read_bytes()).hexdigest()=='b2aecb8d3727f78de6a2bf58deab01d82623097ae0b76e91da7dff65429306d3'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)
before=get();assert before['ui_page']=='vision' and not before['manual_pan']['automatic_following']
settings=R/'face-zone-settings.json';v=json.loads(OLD.read_text())
assert v['left_camera_ratio']==.1 and v['right_ratio']==.7158253629442671
if not settings.exists():
 v.update(board_boot_id='da36c36a-ef4d-4122-8ad6-cfae3931303e',geometry_reused_from=str(OLD),geometry_reused_sha256=hashlib.sha256(OLD.read_bytes()).hexdigest(),updated_mono_ms=int(time.monotonic()*1000))
 with settings.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
else:
 v=json.loads(settings.read_text());assert v['left_camera_ratio']==.1 and v['right_ratio']==.7158253629442671
unit=Path('/etc/systemd/system/aura-face-zone-editor.service')
content=('[Unit]\nDescription=AURA face boundary display\nAfter=aura-avatar-ui.service\nPartOf=aura-avatar-ui.service\n'
 '[Service]\nType=simple\nExecStart=/usr/bin/python3 -B '+str(P)+' --settings '+str(settings)+'\nRestart=on-failure\nRestartSec=3\n'
 '[Install]\nWantedBy=aura-avatar-ui.service\n')
if unit.exists():assert unit.read_text()==content,'Existing service differs; no overwrite'
else:
 with unit.open('x') as f:f.write(content)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=6)
subprocess.run(['systemctl','enable','--now',unit.name],check=True,capture_output=True,text=True,timeout=10)
end=time.monotonic()+6;status=None
while time.monotonic()<end:
 try:
  status=json.loads((R/'face-zone-display-status.json').read_text())
  if status['boot_id']==v['board_boot_id'] and status['active']:break
 except (OSError,ValueError):pass
 time.sleep(.2)
assert status and status['active'],'Boundary display not active'
after=get();assert not after['manual_pan']['automatic_following']
print(json.dumps({'status':'ORIGINAL_REGION_DISPLAY_RESTORED','left_camera_ratio':v['left_camera_ratio'],'right_camera_ratio':(v['right_ratio']*568-84)/400,
 'unit_enabled':True,'editor_pid':subprocess.check_output(['systemctl','show',unit.name,'-p','MainPID','--value'],text=True).strip(),
 'display':status,'preview':after['ui_runtime'].get('preview_metrics'),'motor_commands':0,'MMIO_opened':False,'gui_restarted':False}))
