import json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
base=Path('/home/root/aura-display-sequence-20261024')
result={}
for name,root in [('passive',base/'unattended/c248c0a96ffebb65'),('scheduler',base/'scheduler-observer/06f77083a55985a2')]:
 path=root/('result.json' if (root/'result.json').exists() else 'progress.json')
 value=json.loads(path.read_text())
 keys=['scope','phase','finish_reason','elapsed_seconds','health_queries','query_failures',
  'window','cpu_since_start','native_fault_dumps','trace_validation_passed','cleanup_passed','failure_type','failure',
  'predecessor_elapsed_seconds','handoff_gap_ns','faults_observed_in_handoff_gap','duration_limit_seconds','overall_deadline_mono_ns']
 brief={key:value[key] for key in keys if key in value}
 brief['progress_file']=str(path)
 brief['last_mono_ns']=(value.get('after') or value.get('before') or {}).get('mono_ns')
 brief['captures']=[{key:c[key] for key in ['label','native_report_available','exact_fault_report_available','failure_reason','lease','native_body','release_bookkeeping'] if key in c} for c in value.get('captures',[])]
 for c in brief['captures']:
  for k in ('lease','native_body','release_bookkeeping'):
   if k in c:c[k]={key:v for key,v in c[k].items() if key!='intervals'}
 result[name]=brief
units=['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service',
 'aura-passive-two-hour-c248c0a96ffebb65.service','aura-yunet-sched-06f77083a55985a2.service']
result['units']=subprocess.check_output(['systemctl','show']+units+['-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts'],text=True)
result['display_module_present']=Path('/sys/module/aura_dp_retrain_candidate').exists()
result['uprobe_definitions_empty']=not Path('/sys/kernel/tracing/uprobe_events').read_text().strip()
result['own_trace_instances']=[p.name for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('aura_')]
p=base/'preview-trial/33cfc29f6f7d3dc9'
q=p/('result.json' if (p/'result.json').exists() else 'progress.json')
if q.exists():
 v=json.loads(q.read_text())
 result['preview_trial']={k:v[k] for k in ['phase','active_phase','passed','failure','restoration'] if k in v}
 result['preview_trial']['phases']=[{k:phase[k] for k in ['label','page','seconds','yolo_hz','cpu_busy_percent','gui_group_one_core_percent','preview_hz','avatar_hz','last_rolling_avatar_p95_ms'] if k in phase} for phase in v['phases']]
print(json.dumps(result))
