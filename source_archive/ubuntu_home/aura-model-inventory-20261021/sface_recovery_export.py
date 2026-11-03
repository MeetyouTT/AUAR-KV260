import gzip,base64,hashlib,json,subprocess,urllib.request,time
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
assert h['pid']==588727
names=('board/vision/dpu_vision_schedule.py','board/vision/dpu_recovery_policy.py','board/vision/dpu_sface.py','board/vision/ui_camera_service.py')
files={name:{'sha256':hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest(),'bytes':(root/'aura'/name).stat().st_size} for name in names}
value={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'pid':h['pid'],
 'birth_ticks':int((Path('/proc')/str(h['pid'])/'stat').read_text().rsplit(')',1)[1].split()[19]),
 'captured_mono_ns':time.monotonic_ns(),'schedule':h['dpu_schedule'],'source_manifest':files,
 'feature_inference':h['identity']['feature_inference'],'identity_processed':h['identity']['processed'],
 'face_freshness_counters':h['identity']['face_targets']['freshness_metrics']['counters'],
 'camera_config':json.loads((root/'board_camera_ui.json').read_text()),'root':str(root),
 'camera_unit':Path('/etc/systemd/system/aura-camera-ui.service').read_text()}
data=json.dumps(value,separators=(',',':')).encode()
print(json.dumps({'sha256':hashlib.sha256(data).hexdigest(),'gzip_b64':base64.b64encode(gzip.compress(data,mtime=0)).decode()}))
