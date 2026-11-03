import base64,gzip,hashlib,json,urllib.request
from pathlib import Path
root=Path('/home/root/aura-slot-wait-release-20261023/9d649227aade936c')
d=json.loads((root/'report.json').read_text());assert d['complete'] and d['passed'] and d['accepted']
parent=json.loads(Path('/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json').read_text())
release=Path(d['release']);assert release.resolve()==release
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==d['unit_hashes']['candidate']
files={}
names=['aura/board/identity/face_targets.py','aura/board/identity/face_freshness_metrics.py',
 'aura/board/identity/camera_faces.py','aura/board/vision/dpu_vision_runtime.py',
 'aura/board/vision/dpu_yunet.py','aura/board/vision/ui_camera_service.py',
 'aura/board/vision/dpu_vision_schedule.py','aura/board/vision/dpu_recovery_policy.py',
 'runtime_entry.py','gil_camera_launcher.py','restore_previous.py']
for name in names:
 path=release/name;assert not path.is_symlink();raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if name.startswith('aura/'):
  relative=name[5:];assert sha==d['source_manifest'][relative]['sha256']
 elif name=='runtime_entry.py':assert sha==parent['runtime_entry_sha256']
 elif name=='gil_camera_launcher.py':assert sha=='0cec741d143a012b5d5aa5808f404e7b818510d2773f3b122dd1fb639222ae02'
 else:assert sha==d['rollback_sha256']
 files[name]={'sha256':sha,'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
pid=d['camera_pid'];boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
settings=list((release/'process-settings'/boot).glob('launch-*/process-setting-'+str(pid)+'.json'))
assert len(settings)==1
setting=json.loads(settings[0].read_text());assert setting['pid']==pid and setting['actual_start_seconds']==.001
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as response:h=json.load(response)
assert h['pid']==pid and h['identity']['face_targets']['backend']=='DPU_YUNET_INT8'
out={'release':str(release),'unit_sha256':d['unit_hashes']['candidate'],'boot':boot,'camera_pid':pid,
     'source_files_in_package':len(d['source_manifest']),'process_setting':setting,'files':files}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'files':len(files),'bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
