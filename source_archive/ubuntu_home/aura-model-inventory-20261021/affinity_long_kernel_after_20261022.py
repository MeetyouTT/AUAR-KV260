import json,subprocess,time
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021/affinity-live')
p=sorted(base.glob('*/deployment-result.json'),key=lambda q:q.stat().st_mtime)[-1]
r=json.loads(p.read_text());assert r['complete'] and r['scope']=='CPU_AFFINITY_DUAL_MODEL_600S_ALWAYS_RESTORED'
first=r['samples'][0]['pipeline_metrics']['optional_diagnostics']
last=r.get('fault_camera_snapshot') or r.get('camera_after') or r['latest_camera_seen']
diag=last['pipeline_metrics']['optional_diagnostics']
start=first['started_mono_ns']/1000;end=diag['snapshot_mono_ns']/1000
raw=subprocess.check_output(['journalctl','-k','-n','10000','-o','json','--no-pager'],timeout=8).decode()
rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
stamped=[x for x in rows if x.get('__MONOTONIC_TIMESTAMP') is not None]
window=[x for x in stamped if start<=int(x['__MONOTONIC_TIMESTAMP'])<=end]
warnings=[x for x in window if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
first_mono=int(stamped[0]['__MONOTONIC_TIMESTAMP']) if stamped else None
print(json.dumps({'read_only':True,'read_mono':time.monotonic(),'report_path':str(p),'window_start_mono_us':start,'window_end_mono_us':end,'retained_rows':len(rows),'first_retained_mono_us':first_mono,'window_history_covered':first_mono is not None and first_mono<=start,'matching_warnings_in_candidate_window':len(warnings),'first_matching_mono_us':warnings[0].get('__MONOTONIC_TIMESTAMP') if warnings else None,'last_matching_mono_us':warnings[-1].get('__MONOTONIC_TIMESTAMP') if warnings else None}))
