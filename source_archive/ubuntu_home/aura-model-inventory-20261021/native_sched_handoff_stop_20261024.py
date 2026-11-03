import json,subprocess,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
root=Path('/home/root/aura-display-sequence-20261024/scheduler-observer/84fb117db99251b9')
meta=json.loads((root/'ownership.json').read_text());assert meta['source_sha256'].startswith('84fb117db99251b9')
unit='aura-yunet-sched-84fb117db99251b9.service'
execution=subprocess.check_output(['systemctl','show',unit,'-p','ExecStart','--value'],text=True)
assert '/helpers/84fb117db99251b9/source.py --observe' in execution
subprocess.run(['systemctl','stop',unit],check=True,capture_output=True,text=True,timeout=15)
r=json.loads((root/'result.json').read_text());assert r['phase']=='COMPLETE' and r['cleanup_passed']
assert not Path(meta['trace']).exists()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
assert h['pid']==1291 and not h['dpu_schedule']['owner_fenced']
print(json.dumps({'prior_report':r,'remaining_seconds':max(0,(r['before']['mono_ns']+3600_000_000_000-time.monotonic_ns())/1e9),
 'stopped_only_diagnostic_unit':unit,'model_pid_unchanged':True}))
