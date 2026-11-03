import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def camera():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:return json.load(stream)
h=camera();s=h['dpu_schedule'];f=h['identity']['face_targets']
release=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb')
names=['board/vision/dpu_vision_schedule.py','board/vision/dpu_sface.py','board/vision/ui_camera_service.py','board/vision/dpu_protection_handoff.py']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/board_identity.sface_int8.json')
services={}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
 text=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','NRestarts'],text=True)
 services[unit]=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
tracing=Path('/sys/kernel/tracing')
probes=[row.split()[0] for row in (tracing/'uprobe_events').read_text().splitlines() if any(n in row for n in ('aura_optional_','aura_iso_','aura_vart_'))]
instances=[p.name for p in (tracing/'instances').iterdir() if p.name.startswith(('aura_optional_','aura_iso_','aura_vart_'))]
nice={p.name:os.getpriority(os.PRIO_PROCESS,int(p.name)) for p in (Path('/proc')/str(h['pid'])/'task').iterdir()}
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto/stat')
counter_before=[int(v) for v in cu.read_text().split()];time.sleep(1.5)
after=camera();counter_after=[int(v) for v in cu.read_text().split()]
print(json.dumps({'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'mono_ns':time.monotonic_ns(),'pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':s['optional'],
 'yunet_recovery':s['yunet_recovery'],'sface_recovery':s['sface_recovery'],'owner_fenced':s['owner_fenced'],
 'primary_overruns':s['primary_period_overruns'],'backend':f['backend'],'worker_alive':f['worker_alive'],
 'gap_count':f['freshness_metrics']['counters']['observed_gap_intervals'],'feature_inference':h['identity']['feature_inference'],
 'fault_events':s['optional_diagnostics']['fault_events'],'services':services,
 'unit_sha256':sha('/etc/systemd/system/aura-camera-ui.service'),
 'persistent_override_sha256':sha('/etc/systemd/system/aura-camera-ui.service.d/zzzz-aura-vision-recovery-c76110abefc304bb.conf'),
 'source_sha256':{n:sha(release/'aura'/n) for n in names},'identity_config_sha256':sha(identity),
 'database_sha256':sha(json.loads(identity.read_text())['database']),
 'own_uprobe_definitions':probes,'own_instances':instances,'thread_nice':nice,
 'cu_statistics_stopped_while_real_frames_progress':(h['pid']==after['pid'] and counter_before==counter_after
    and after['detected_frames']-h['detected_frames']>=5),
 'real_detected_frames_during_check':after['detected_frames']-h['detected_frames']}))
