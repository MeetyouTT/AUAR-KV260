import json
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a')
s=json.loads((R/'state.json').read_text());assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
l=json.loads((R/'readonly-watch-launch.json').read_text());p=Path(l['output'])
status=json.loads((p/'status.json').read_text());rows=[json.loads(x) for x in (p/'samples.jsonl').read_text().splitlines()]
windows=[r for r in rows if 'kernel_window_s' in r]
cp=json.loads(Path(s['checkpoint']).read_text())
print(json.dumps({'boot_id':s['boot'],'watch_status':status,'recorded_samples':len(rows),
 'read_errors':sum('error' in r for r in rows),'kernel_windows':len(windows),
 'sampled_xhci_warnings':sum(r['xhci_buffer_warnings'] for r in windows),
 'capped_kernel_windows':sum(r['kernel_sample_capped'] for r in windows),
 'following_true_samples':sum(r.get('automatic_following') is True for r in rows),
 'primary_before_normal_stop':s['counters_before']['primary_overruns'],
 'primary_at_fresh_checkpoint':cp['seed']['primary_period_overruns'],
 'primary_latest':status.get('latest',{}).get('primary_overruns'),
 'motor_commands_sent':0,'scope':'bounded read-only observer; no physical smoothness validation'}))
