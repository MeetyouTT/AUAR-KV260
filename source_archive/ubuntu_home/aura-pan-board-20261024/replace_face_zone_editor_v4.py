"""Correct face-overlay letterboxing, retaining the chosen physical line."""
import hashlib,json,subprocess,time
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');p=R/'face-zone-settings.json'
before=json.loads(p.read_text());source=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/zone-editor-v4/face_zone_editor.py')
assert source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()=='e2d4477daef1d98f486d9c8c104ab363fccb7ff5dddc2609b70cab91b65b2d76';unit='aura-face-zone-editor.service'
stopped=subprocess.run(['systemctl','stop',unit],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
assert stopped.returncode in (0,5),stopped.stderr[-400:]
subprocess.run(['systemd-run','--quiet','--collect','--unit=aura-face-zone-editor','--property=Restart=no','/usr/bin/python3','-B',str(source),'--settings',str(p)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
time.sleep(1);after=json.loads(p.read_text());assert before['right_ratio']==after['right_ratio']
print(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'line_unchanged':True,'settings':after,'camera_restarted':False,'gui_restarted':False,'motor_commands':0}))
