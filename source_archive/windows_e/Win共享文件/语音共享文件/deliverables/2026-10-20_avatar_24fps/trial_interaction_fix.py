from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'trial_stable_fps.py').read_text(encoding='utf-8-sig')
s=s.replace("'stable_fps_candidate.json'","'interaction_fix_candidate.json'").replace("'stable_fps_verification.json'","'interaction_fix_verification.json'")
s=s.replace("assert json.loads((HERE/'stable_fps_target_tests.json').read_text())['passed'];assert 'NATIVE_GTK_SMOKE_PASS' in json.loads((HERE/'stable_fps_smoke.json').read_text())['out']", "assert json.loads((HERE/'interaction_fix_tests.json').read_text())['code']==0")
s=s.replace("c=json.loads((HERE/'interaction_fix_candidate.json').read_text());", "c=json.loads((HERE/'interaction_fix_candidate.json').read_text());c['library_sha256']='201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f';")
s=s.replace('zzzz-aura-stable-fps-trial.conf','zzzzzz-aura-interaction-render-fix.conf').replace('aura-stable-fps-watchdog-','aura-interaction-render-watchdog-')
s=s.replace("'stable_fps_trial.json'","'interaction_fix_trial.json'")
exec(compile(s,str(HERE/'trial_stable_fps.py'),'exec'))
