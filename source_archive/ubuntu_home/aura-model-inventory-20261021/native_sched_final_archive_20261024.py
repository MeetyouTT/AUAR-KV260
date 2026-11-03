import json,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
p=Path('/home/root/aura-display-sequence-20261024/scheduler-observer/06f77083a55985a2/result.json')
report=json.loads(p.read_text());assert report['phase']=='COMPLETE' and report['cleanup_passed']
k=Path('/sys/kernel/debug/kprobes/list');symbols=['zynqmp_dp_train_loop','zynqmp_dp_irq_handler','drm_mode_getresources']
text=k.read_text() if k.exists() else None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
assert h['pid']==1291 and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced']
print(json.dumps({'scheduler_report':report,'residuals':{
 'trace_instances':[p.name for p in Path('/sys/kernel/tracing/instances').iterdir() if p.name.startswith('aura_')],
 'uprobe_definitions_empty':not Path('/sys/kernel/tracing/uprobe_events').read_text().strip(),
 'display_module_absent':not Path('/sys/module/aura_dp_retrain_candidate').exists(),
 'kprobe_list_sampled':text is not None,'target_kprobe_counts':{s:sum(s in line for line in text.splitlines()) for s in symbols} if text is not None else None},
 'camera':{'pid':h['pid'],'yolo_hz':h['detection_hz'],'worker_alive':h['identity']['face_targets']['worker_alive'],
 'sface_ready':h['identity']['feature_inference']['ready'],'optional_faults':{k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()}},
 'display_DPMS':Path('/sys/class/drm/card0-DP-1/dpms').read_text().strip()}))
