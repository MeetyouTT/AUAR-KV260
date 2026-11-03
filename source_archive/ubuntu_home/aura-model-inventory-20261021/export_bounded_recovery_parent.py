import base64,gzip,hashlib,json
from pathlib import Path
report=Path('/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json')
d=json.loads(report.read_text());assert d['complete'] and d['passed'] and d['accepted']
root=Path(d['release']);assert root.resolve()==root
unit=Path('/etc/systemd/system/aura-camera-ui.service')
assert hashlib.sha256(unit.read_bytes()).hexdigest()==d['unit_sha256']
files={}
for name in ('board/vision/dpu_vision_schedule.py','board/vision/dpu_yunet.py','board/vision/ui_camera_service.py'):
    p=root/'aura'/name;assert not p.is_symlink();raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    assert sha==d['source_manifest'][name]['sha256']
    files[name]={'sha256':sha,'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
out={'release':str(root),'unit_sha256':d['unit_sha256'],
     'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'files':files}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
