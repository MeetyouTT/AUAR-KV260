import base64,gzip,hashlib,json
from pathlib import Path
d=json.loads(Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669/report.json').read_text())
assert d['complete'] and d['passed'] and d['accepted']
release=Path(d['release']);files={}
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==d['unit_sha256']
for name,digest in d['candidate_pins'].items():
 gui=name=='board/identity/spoken_query.py';p=(Path(d['gui_runtime']) if gui else release)/'aura'/name
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 files[('gui/aura/' if gui else 'camera/aura/')+name]={'sha256':digest,'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
for name in ('runtime_entry.py','gil_camera_launcher.py','restore_previous.py'):
 p=release/name;raw=p.read_bytes();files['camera/'+name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
payload={'release':d['release'],'gui_runtime':d['gui_runtime'],'unit_sha256':d['unit_sha256'],
 'camera_pid':d['camera_pid'],'gui_pid':d['gui_pid'],'camera_package_files':len(d['source_manifest']),
 'gui_source_files':len(d['gui_sources_after']),'files':files}
raw=json.dumps(payload,separators=(',',':')).encode()
print(json.dumps({'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode(),'files':len(files)}))
