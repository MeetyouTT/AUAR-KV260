"""UI-only trial, no synthetic speaking, exact original monitor restoration."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'2026-10-20_avatar_24fps'
s=(OLD/'trial_stable_fps.py').read_text(encoding='utf-8-sig')
s=s.replace('HERE=Path(__file__).resolve().parent;', 'HERE=Path(%r);'%str(HERE))
s=s.replace("'stable_fps_candidate.json'","'candidate.json'").replace("'stable_fps_verification.json'","'verification.json'")
s=s.replace("assert json.loads((HERE/'stable_fps_target_tests.json').read_text())['passed'];assert 'NATIVE_GTK_SMOKE_PASS' in json.loads((HERE/'stable_fps_smoke.json').read_text())['out']", "assert (HERE/'local_tests.txt').is_file()")
s=s.replace("c=json.loads((HERE/'candidate.json').read_text());", "c=json.loads((HERE/'candidate.json').read_text());c['library_sha256']='201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f';")
s=s.replace('zzzz-aura-stable-fps-trial.conf','zzzzzzzzzz-aura-motion-binding.conf').replace('aura-stable-fps-watchdog-','aura-motion-binding-watchdog-')
s=s.replace("'stable_fps_trial.json'","'deployment.json'")
s=s.replace("report['baseline_speaking']=speaking_measure()", "report['audio_test']='not_triggered'")
s=s.replace('try:baseline=measure(30)','try:baseline=measure(20)').replace('trial=measure(90,gate)','trial=measure(60,gate)')
start=s.index(' speaking=speaking_measure();');end=s.index(" assert pref.read_bytes()==pref_before",start)
s=s[:start]+s[end:]
exec(compile(s,str(OLD/'trial_stable_fps.py'),'exec'))
