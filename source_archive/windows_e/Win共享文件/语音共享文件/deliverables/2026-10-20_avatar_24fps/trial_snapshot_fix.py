from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'trial_stable_fps.py').read_text(encoding='utf-8-sig')
s=s.replace("'stable_fps_candidate.json'","'snapshot_fix_candidate.json'").replace("'stable_fps_verification.json'","'snapshot_fix_verification.json'")
s=s.replace("assert json.loads((HERE/'stable_fps_target_tests.json').read_text())['passed']", "assert json.loads((HERE/'snapshot_fix_tests.json').read_text())['passed']")
s=s.replace("'stable_fps_smoke.json'","'snapshot_fix_smoke.json'")
s=s.replace("c=json.loads((HERE/'snapshot_fix_candidate.json').read_text());", "c=json.loads((HERE/'snapshot_fix_candidate.json').read_text());c['library_sha256']='201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f';")
s=s.replace('zzzz-aura-stable-fps-trial.conf','zzzzzzz-aura-snapshot-budget.conf').replace('aura-stable-fps-watchdog-','aura-snapshot-budget-watchdog-')
s=s.replace("'stable_fps_trial.json'","'snapshot_fix_trial.json'")
s=s.replace(" if before['handsfree_dialogue']['enabled']:toggle_monitor(True)\n assert get()['handsfree_dialogue']['enabled']==before['handsfree_dialogue']['enabled']", """ performance=get()['avatar_renderer']['presentation']['performance_log']
 assert not performance['error'] and performance['written']>=10,'Performance logger not healthy'
 logs=list((Path(c['runtime'])/'managed-runs').glob('*/evidence/render_performance.jsonl'))
 assert logs,'No phase performance records'
 rows=[json.loads(line) for p in logs for line in p.read_text().splitlines()]
 assert any(x['phase']=='SPEAKING' and x['frames']>=2 for row in rows for x in row['phases']),'Speaking phase not recorded'
 report['phase_log']={'records':len(rows),'phases':sorted({x['phase'] for row in rows for x in row['phases']}),'status':performance}
 if before['handsfree_dialogue']['enabled']:toggle_monitor(True)
 assert get()['handsfree_dialogue']['enabled']==before['handsfree_dialogue']['enabled']""")
exec(compile(s,str(HERE/'trial_stable_fps.py'),'exec'))
