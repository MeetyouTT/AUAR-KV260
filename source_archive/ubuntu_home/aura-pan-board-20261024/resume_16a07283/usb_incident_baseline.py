"""Read current USB metadata once; this is not a detected warning incident."""
import hashlib,importlib.util,json,time,urllib.request
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/usb-incidents-v1')
p=P/'usb_incident_capture.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='c7f423236faf2576a63eac753848672771e4ac0c8cb06aab78b6b7545eea3759'
spec=importlib.util.spec_from_file_location('incident_capture',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
R=Path('/home/root/aura-pan-current-20261024/16a07283');state=json.loads((R/'state.json').read_text())
platform=m.Platform(state['current_camera_pid'],state['current_gui_pid'])
before=platform.check();assert not before['automatic_following'] and before['flags']==0 and before['lease_ms']==0
captured=platform.capture(time.monotonic,time.sleep,time.monotonic()+12)
after=platform.check();assert after['flags']==0 and after['lease_ms']==0 and not after['automatic_following']
assert before['width_us']==after['width_us']
print(json.dumps({'status':'READONLY_INCIDENT_BASELINE_METADATA_PASS','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
 'captured':captured,'warning_observed':False,'motor_commands_sent':0,'automatic_recovery':False,
 'scope':'explicit baseline; no injected warning; numeric metadata only'}))
