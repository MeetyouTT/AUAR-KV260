import json
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
launch=root/'launch-result.json';reports=sorted((root/'runs').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
out={'launch':json.loads(launch.read_text()) if launch.exists() else None,'report_path':str(reports[-1]) if reports else None}
b_launch=root/'b-long-600-launch-result.json';out['b_only_launch']=json.loads(b_launch.read_text()) if b_launch.exists() else None
if reports:
 r=json.loads(reports[-1].read_text());out['summary']={k:r.get(k) for k in ('phase','passed','complete','error','conclusion','retry_target_met','rollback_verified','rollback_error','rollback_timer_left_armed','completion_rate_ratio')};out['variants']={}
 for name,v in r.get('variants',{}).items():
  value={k:v.get(k) for k in ('pid','complete','functional_passed','elapsed_s','observed_seconds','observed_yolo_hz','observed_yunet_hz','sface_completed_window','sface_hz','prepared_crops_window','one_face_samples','source_coverage_ok','stage_targets_met','rollback_verified')}
  s=v.get('latest_camera_seen') or {};value['shadow']=s.get('shadow');value['producer']=s.get('producer');value['optional']=(s.get('dpu_schedule') or {}).get('optional');out['variants'][name]=value
 if r.get('restored'):out['restored_pid']=r['restored']['pid']
print(json.dumps(out))
