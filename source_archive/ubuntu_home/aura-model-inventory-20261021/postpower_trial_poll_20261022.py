import json
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
out={}
for kind,folder in [('metrics','postpower-metrics-live'),('retry','postpower-retry-live')]:
 files=sorted((base/folder).glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
 if not files:continue
 p=files[-1];r=json.loads(p.read_text());state=r.get('camera_after') or r.get('fault_camera_snapshot') or r.get('latest_camera_seen') or {}
 face=state.get('face_targets') or {};light=face.get('freshness_metrics') or {}
 out[kind]={'path':str(p),'summary':{k:r.get(k) for k in ('scope','passed','complete','phase','error','elapsed_s','observed_seconds','observed_yolo_hz','observed_yunet_hz','cpu_window','usb_warning_count','rollback_verified','rollback_error')},
  'optional':state.get('dpu_schedule',{}).get('optional'),'faults':state.get('pipeline_metrics',{}).get('optional_diagnostics',{}).get('fault_events'),
  'face':{k:face.get(k) for k in ('backend','ready','error','processed','discarded','source_age_ms','slot_retry')},
  'freshness_counters':light.get('counters'),'freshness_summaries':light.get('summaries'),
  'samples':r.get('sample_count',len(r.get('samples',[]))),'restored_pid':r.get('restored',{}).get('pid')}
launches={}
for folder in ('postpower-metrics-launches','postpower-retry-launches'):
 files=sorted((base/folder).glob('*/launch-result.json'),key=lambda p:p.stat().st_mtime)
 if files:launches[folder]=json.loads(files[-1].read_text())
out['launches']=launches
print(json.dumps(out))
