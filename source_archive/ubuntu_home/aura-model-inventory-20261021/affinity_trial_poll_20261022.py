import json
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
launch=base/'affinity-launches/c98cdd3015a36636/launch-result.json'
reports=sorted((base/'affinity-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
out={'launch':json.loads(launch.read_text()) if launch.exists() else None}
long_launch=base/'affinity-long-launches/3a1fd27e0d2126a5/launch-result.json'
out['long_launch']=json.loads(long_launch.read_text()) if long_launch.is_file() else None
if reports:
 p=reports[-1];r=json.loads(p.read_text());last=r.get('camera_after') or r.get('fault_camera_snapshot') or r.get('latest_camera_seen') or {}
 diag=(last.get('pipeline_metrics') or {}).get('optional_diagnostics',{})
 out.update(report_path=str(p),summary={k:r.get(k) for k in ('scope','phase','passed','complete','error','candidate_camera_pid','elapsed_s','observed_seconds','observed_yolo_hz','observed_yunet_hz','cpu_window','usb_warning_count','freshness','throughput_and_optional_protection_passed','rollback_verified','rollback_error','affinity_shutdown_error')},optional=(last.get('dpu_schedule') or {}).get('optional'),faults=diag.get('fault_events'),face_targets=last.get('face_targets'),sample_count=len(r.get('samples',[])),affinity_start=r.get('affinity_start'),restored_pid=r.get('restored',{}).get('pid'),affinity_shutdown_clean=r.get('affinity_shutdown',{}).get('clean_selected_thread_restoration_and_close'))
print(json.dumps(out))
