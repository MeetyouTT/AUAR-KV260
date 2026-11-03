import json,time
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
launches=sorted((base/'merged-live-launches').glob('*/launch-result.json'),key=lambda p:p.stat().st_mtime)
reports=sorted((base/'merged-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
out={'launch':json.loads(launches[-1].read_text()) if launches else None,'report_path':str(reports[-1]) if reports else None}
if reports:
 v=json.loads(reports[-1].read_text());out['summary']={k:v.get(k) for k in ('scope','phase','passed','complete','error','rollback_error','observation_status','elapsed_s','observed_seconds','observed_yolo_hz','observed_capture_hz','observed_yunet_hz','shadow_completed_window','sface_live_verified','usb_warning_count','rollback_verified','restored')}
 out['samples']=len(v.get('samples',[]));s=v.get('latest_camera_seen') or {};out['latest_camera']={k:s.get(k) for k in ('pid','shadow','producer','face_targets','dpu_schedule')}
print(json.dumps(out))
