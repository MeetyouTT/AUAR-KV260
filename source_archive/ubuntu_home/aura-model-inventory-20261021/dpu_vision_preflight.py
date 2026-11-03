import base64,gzip,hashlib,json,os
from pathlib import Path
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'processes':[], 'sources':{}}
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except (OSError,UnicodeError):continue
 if 'board_camera_motion.py' not in cmd:continue
 if 'python' not in cmd:continue
 args=(proc/'cmdline').read_bytes().split(b'\0')
 script=next((Path(x.decode()) for x in args if x.endswith(b'/board_camera_motion.py')),None)
 if script is None:continue
 result['processes'].append({'pid':int(proc.name),'command':cmd[:1200]})
 root=script.parent.parent
 for rel in ['tools/board_camera_motion.py','board/vision/ui_camera_service.py','board/vision/dpu_schedule.py','board/identity/dpu_sface.py','board/identity/manager.py','board/identity/service.py']:
  p=root/rel
  if p.is_file() and p.stat().st_size<250000:
   data=p.read_bytes();result['sources'][rel]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'gz_base64':base64.b64encode(gzip.compress(data)).decode()}
 for x in args:
  try:p=Path(x.decode())
  except (UnicodeError,ValueError):continue
  if p.is_absolute() and p.suffix=='.json' and p.is_file():
   data=p.read_bytes()
   result.setdefault('configs',{})[str(p)]={'sha256':hashlib.sha256(data).hexdigest(),'content':json.loads(data)}
print(json.dumps(result))
