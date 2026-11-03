import base64,gzip,hashlib,json
from pathlib import Path
report=Path('/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json')
d=json.loads(report.read_text());assert d['complete'] and d['passed'] and d['accepted']
root=Path(d['release']);assert root.resolve()==root
files={}
names=['aura/board/identity/face_targets.py','aura/board/identity/face_freshness_metrics.py',
 'aura/board/identity/camera_faces.py','aura/board/vision/dpu_vision_runtime.py',
 'aura/board/vision/dpu_yunet.py','aura/board/vision/ui_camera_service.py',
 'runtime_entry.py','gil_camera_launcher.py','restore_original.py']
for name in names:
 p=root/name;assert not p.is_symlink();raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if name.startswith('aura/'):assert sha==d['source_manifest'][name[5:]]['sha256']
 elif name=='runtime_entry.py':assert sha==d['runtime_entry_sha256']
 files[name]={'sha256':sha,'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
out={'release':str(root),'unit_sha256':d['unit_sha256'],'accepted':d['accepted'],
 'activation_report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
 'activation':{k:d.get(k) for k in ('scope','passed','complete','accepted','phase','observed_seconds','yolo_hz','yunet_hz',
   'cpu_window','usb_warning_count','source_manifest_sha256','unit_sha256','runtime_entry_sha256','guard_state','guard_left_armed','error')},
 'files':files}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'files':len(files),'bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
