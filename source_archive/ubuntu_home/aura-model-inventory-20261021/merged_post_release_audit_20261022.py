import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    with opener.open('http://127.0.0.1:8790/health',timeout=3) as r:return json.load(r)
s=health();args=(Path('/proc')/str(s['pid'])/'cmdline').read_bytes().split(b'\0')
script=next(Path(a.decode()) for a in args if a.endswith(b'/board_camera_motion.py'))
root=script.parent.parent;config=Path(args[args.index(b'--config')+1].decode());c=json.loads(config.read_text())
identity=Path(c['identity']['config']);i=json.loads(identity.read_text())
original=Path('/home/root/aura-handsfree-dialogue-20261020/candidate-0c0a8ab46ec2/camera_live_config/board_identity.json');old=json.loads(original.read_text())
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'pid':s['pid'],'runtime':str(root),'camera_config':str(config),'identity_config':str(identity),'camera_unit_sha256':sha('/etc/systemd/system/aura-camera-ui.service'),
     'face_backend_kind':i.get('face_backend',{}).get('kind'),'feature_backend':i.get('feature_backend'),'original_database_path_preserved':i['database']==old['database'],
     'face_backend_hashes_verified':False,'units':{},'source_hashes':{},'active_owned_rollback_timers':[]}
backend=i.get('face_backend',{})
assert backend.get('kind')=='dpu_yunet'
assert all(sha(backend[k])==backend[k+'_sha256'] for k in ('model','manifest'))
out['face_backend_hashes_verified']=True
out['model_sha256']=sha(backend['model']);out['manifest_sha256']=sha(backend['manifest'])
for name in ['board/identity/camera_faces.py','board/identity/face_targets.py','board/vision/ui_camera_service.py','board/vision/dpu_yunet.py','board/vision/dpu_vision_runtime.py','board/vision/dpu_vision_schedule.py']:
    out['source_hashes'][name]=sha(root/name)
for name in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','systemd-journald.service']:
    out['units'][name]=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=4).decode().strip()
for prefix in ['aura-yunet-pilot-rollback-','aura-audio-recovery-','aura-sface-shadow-rollback-','aura-capture-copy-live-rollback-','aura-merged-live-rollback-']:
    for p in Path('/run/systemd/transient').glob(prefix+'*.timer'):
        state=subprocess.check_output(['systemctl','show',p.name,'-p','ActiveState','--value'],timeout=3).decode().strip()
        if state=='active':out['active_owned_rollback_timers'].append(p.name)
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto/stat')
first=cu.read_text().split()[0];time.sleep(.4);second=cu.read_text().split()[0]
out['cu_collector_inactive']=first==second
last=health();out['detection_advanced']=last['detected_frames']>s['detected_frames']
out['dpu_schedule']=last.get('dpu_schedule');out['face_targets']=last.get('identity',{}).get('face_targets')
out['sface_shadow_absent']=not ((last.get('identity',{}).get('feature_inference') or {}).get('shadow'))
assert out['camera_unit_sha256']=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
assert root==Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/aura')
assert out['sface_shadow_absent']
assert i.get('feature_backend',{}).get('kind')=='windows_sface' and out['original_database_path_preserved']
assert out['detection_advanced'] and out['cu_collector_inactive'] and not out['active_owned_rollback_timers']
assert out['face_targets']['backend']=='DPU_YUNET_INT8'
assert last.get('pipeline_metrics') is None
out['pipeline_metrics_disabled']=True
print(json.dumps(out))
