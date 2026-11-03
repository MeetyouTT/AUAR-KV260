import json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');S=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v15/stage-state.json')
s=json.loads((R/'state.json').read_text());t=json.loads(S.read_text());assert t['phase']=='CAMERA_READY_WITH_MOTION_FEED'
assert s['boot']==t['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert h['pid']==t['camera_pid'] and not h['dpu_schedule']['owner_fenced']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
s.update(phase='R12_SOURCE_V15_PROFILE_READY_OUTPUT_STOPPED',current_camera_pid=h['pid'],face_source_version=15,
 face_tracking_algorithm_version=14,automatic_following=False,current_gui_pid=t['gui_pid'])
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'camera_pid':h['pid'],'gui_pid':t['gui_pid'],'readback':m['readback'],
 'identity_ready':h['identity']['ready'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},'new_motion_requested':False}))
