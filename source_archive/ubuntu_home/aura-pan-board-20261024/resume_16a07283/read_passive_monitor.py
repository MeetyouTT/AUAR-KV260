import collections,json,time
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
m=json.loads((R/'passive-monitor-latest.json').read_text());P=Path(m['output'])
s=json.loads((P/'status.json').read_text());rows=[]
for line in (P/'samples.jsonl').read_text().splitlines():
 try:rows.append(json.loads(line))
 except ValueError:pass
warnings=[x for x in rows if x.get('xhci_buffer_warnings',0)]
errors=[x for x in rows if x.get('error')]
print(json.dumps({'status':s,'samples':len(rows),'first':rows[:1],'last':rows[-1:],
 'observed_seconds':round(rows[-1]['elapsed_s']-rows[0]['elapsed_s'],3) if rows else 0,
 'kernel_windows':sum('kernel_lines_sampled' in x for x in rows),'warning_windows':len(warnings),
 'warning_count_in_bounded_samples':sum(x.get('xhci_buffer_warnings',0) for x in rows),
 'capped_kernel_windows':sum(x.get('kernel_sample_capped',False) for x in rows),
 'read_errors':len(errors),'errors':errors[-3:],'motion_seen':sum(x.get('automatic_following',False) for x in rows),
 'owner_pids':sorted(set(x.get('camera_pid',0) for x in rows)),
 'primary_overruns_first_last':[rows[0].get('primary_overruns'),rows[-1].get('primary_overruns')] if rows else [],
 'motor_commands_sent_by_monitor':0,'output':str(P)}))
