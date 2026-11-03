import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera':{k:s.get(k) for k in ['pid','detected_frames','capture_hz','detection_hz','camera_error','detector_error','observation_age_ms','dpu_schedule']},
 'identity_backend':s.get('identity',{}).get('backend'),'units':{}}
args=(Path('/proc')/str(s['pid'])/'cmdline').read_bytes().split(b'\0');script=next(Path(a.decode()) for a in args if a.endswith(b'/board_camera_motion.py'))
config=Path(args[args.index(b'--config')+1].decode());cfg=json.loads(config.read_text());identity=json.loads(Path(cfg['identity']['config']).read_text())
out['active_camera_runtime']=str(script.parent.parent);out['face_backend']=identity.get('face_backend');out['feature_backend_kind']=identity.get('feature_backend',{}).get('kind')
original=Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e/camera.service.original')
out['camera_unit_restored']=Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()==original.read_bytes()
for name in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
 out['units'][name]=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=5).decode()
root=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit')
out['three_model_fixed_test_passed']=json.loads((root/'board-result.json').read_text())['passed']
p=root/'sface_public_int8.xmodel';out['sface_candidate_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto/stat');first=cu.read_text();time.sleep(.4);second=cu.read_text()
out['cu_collector_inactive']=first.split()[0]==second.split()[0]
with opener.open('http://127.0.0.1:8790/health',timeout=2) as r:last=json.load(r)
out['detection_advanced']=last['detected_frames']>s['detected_frames']
out['owned_restore_timers']={}
for prefix in ['aura-yunet-pilot-rollback-','aura-dpu-vision-restore-']:
 for p in Path('/run/systemd/transient').glob(prefix+'*.timer'):
  state=subprocess.check_output(['systemctl','show',p.name,'-p','ActiveState','--value'],timeout=5).decode().strip()
  out['owned_restore_timers'][p.name]=state
assert all(v!='active' for v in out['owned_restore_timers'].values()),'An owned rollback timer is still armed'
assert out['camera_unit_restored'] and out['face_backend'] is None and out['feature_backend_kind']=='windows_sface'
assert out['three_model_fixed_test_passed'] and out['cu_collector_inactive'] and out['detection_advanced']
assert not s['camera_error'] and not s['detector_error']
print(json.dumps(out))
