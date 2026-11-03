import json
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
reports=sorted((base/'thread-switch-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
launches=sorted((base/'thread-switch-launches').glob('*/launch-result.json'),key=lambda p:p.stat().st_mtime)
out={'launch':json.loads(launches[-1].read_text()) if launches else None,'report_path':str(reports[-1]) if reports else None}
if reports:
 r=json.loads(reports[-1].read_text());out['summary']={k:r.get(k) for k in ('phase','passed','complete','error','elapsed_s','observed_seconds','observed_yolo_hz','observed_capture_hz','usb_warning_count','rollback_verified','rollback_error','rollback_timer_left_armed')}
 s=r.get('latest_camera_seen') or {};d=(s.get('pipeline_metrics') or {}).get('optional_diagnostics') or {}
 out['observer']=d.get('thread_sched_observer');out['faults']=d.get('fault_events');out['optional']=(s.get('dpu_schedule') or {}).get('optional');out['samples']=len(r.get('samples',[]))
 if r.get('restored'):out['restored_pid']=r['restored']['pid']
print(json.dumps(out))
