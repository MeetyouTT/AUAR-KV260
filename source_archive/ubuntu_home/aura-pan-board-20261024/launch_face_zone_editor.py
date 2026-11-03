"""Launch a small separate boundary overlay without restarting video/GUI."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
source=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/zone-editor-v1/face_zone_editor.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='6b7829675d563d9e4d716bc9d093d3f7d8f5edc0b2d97a76c7306c88b33e60fb'
settings=Path('/home/root/aura-pan-current-20261024/463c9307/face-zone-settings.json');unit='aura-face-zone-editor.service'
state=subprocess.run(['systemctl','is-active',unit],stdout=subprocess.PIPE,text=True).stdout.strip();assert state!='active'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as reply:u=json.load(reply)
assert u['manual_pan']['state']=='READY' and not u['manual_pan']['automatic_following'] and u['manual_pan']['readback']['flags']==0
subprocess.run(['systemd-run','--quiet','--collect','--unit=aura-face-zone-editor','--property=Restart=no','/usr/bin/python3','-B',str(source),'--settings',str(settings)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
end=time.monotonic()+10;ready=False
while time.monotonic()<end:
 p=subprocess.run(['systemctl','is-active',unit],stdout=subprocess.PIPE,text=True)
 if p.stdout.strip()=='active' and settings.is_file():ready=True;break
 if p.stdout.strip()=='failed':break
 time.sleep(.2)
status=subprocess.run(['systemctl','status',unit,'--no-pager','-n','10'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout[-4000:]
print(json.dumps({'editor_ready':ready,'settings':json.loads(settings.read_text()) if settings.exists() else None,'unit':status,'camera_restarted':False,'gui_restarted':False,'motor_commands':0}))
