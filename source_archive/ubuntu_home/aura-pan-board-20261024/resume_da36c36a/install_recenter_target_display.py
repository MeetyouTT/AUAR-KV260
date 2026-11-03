import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
P=F/'zone-editor-recenter-v1/face_zone_editor.py'
assert hashlib.sha256(P.read_bytes()).hexdigest()=='61e1c51a7b5439daeadff36d30f37e08e015b0e6a7840ece3a0dc32dd9d90595'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
assert u['manual_pan']['state']=='READY' and not u['manual_pan']['automatic_following']
assert u['manual_pan']['readback']['flags']==0 and u['manual_pan']['readback']['lease_left_ms']==0
unit=Path('/etc/systemd/system/aura-face-zone-editor.service');raw=unit.read_bytes()
assert str(F/'zone-editor-v8/face_zone_editor.py') in raw.decode() and 'PartOf=aura-avatar-ui.service' in raw.decode()
with (R/'zone-editor-service-before-recenter').open('xb') as f:f.write(raw)
subprocess.run(['systemctl','stop',unit.name],check=True,timeout=10)
settings=R/'face-zone-settings.json';old=settings.read_bytes()
with (R/'face-zone-settings-before-recenter.json').open('xb') as f:f.write(old)
value=json.loads(old);value.update(recenter_on_edge=True,target_center_ratio=.5,center_tolerance_ratio=.03)
tmp=settings.with_name(settings.name+'.recenter');tmp.write_text(json.dumps(value,indent=2)+'\n');os.replace(tmp,settings)
new=raw.decode().replace(str(F/'zone-editor-v8/face_zone_editor.py'),str(P))
tmp=unit.with_name(unit.name+'.recenter');tmp.write_text(new);os.replace(tmp,unit)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=6)
subprocess.run(['systemctl','start',unit.name],check=True,timeout=6)
end=time.monotonic()+6;display={}
while time.monotonic()<end:
 try:
  display=json.loads((R/'face-zone-display-status.json').read_text())
  if display.get('recenter_mode') and display.get('active'):break
 except (OSError,ValueError):pass
 time.sleep(.2)
assert display.get('recenter_mode') and display.get('active')
print(json.dumps({'status':'CENTER_TARGET_DISPLAY_ACTIVE','display':display,'original_left_ratio':value['left_camera_ratio'],
 'original_right_widget_ratio':value['right_ratio'],'target_center_ratio':.5,'motor_commands':0,'MMIO_opened':False,'gui_restarted':False}))
