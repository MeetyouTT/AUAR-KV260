import hashlib,json
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb')
files={}
for name in ['runtime_entry.py','board_camera_ui.json']:
 raw=(root/name).read_bytes();files[name]={'sha256':hashlib.sha256(raw).hexdigest()}
 if name.endswith('.py'):files[name]['source']=raw.decode()
 else:
  value=json.loads(raw);files[name]['identity']=value['identity'];files[name]['thread_waits']={k:value.get(k) for k in ['yunet_slot_wait_ms','sface_slot_wait_ms','optional_admission_floor_ms']}
print(json.dumps({'files':files}))
