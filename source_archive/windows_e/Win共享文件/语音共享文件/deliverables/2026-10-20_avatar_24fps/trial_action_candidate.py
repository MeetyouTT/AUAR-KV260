"""Reuse rollback/preservation gates, retaining the accepted 8fps frame budget."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'trial_stable_fps.py').read_text(encoding='utf-8-sig')
source=source.replace("'stable_fps_candidate.json'","'action_candidate.json'")
source=source.replace("'stable_fps_verification.json'","'action_verification.json'")
source=source.replace("assert json.loads((HERE/'stable_fps_target_tests.json').read_text())['passed']",
                      "assert json.loads((HERE/'action_connection_tests.json').read_text())['code']==0")
source=source.replace("'stable_fps_smoke.json'","'action_smoke.json'")
source=source.replace("c=json.loads((HERE/'action_candidate.json').read_text());", "c=json.loads((HERE/'action_candidate.json').read_text());c['library_sha256']='201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f';")
source=source.replace('zzzz-aura-stable-fps-trial.conf','zzzzz-aura-speech-motion-trial.conf')
source=source.replace('aura-stable-fps-watchdog-','aura-speech-motion-watchdog-')
source=source.replace("'stable_fps_trial.json'","'action_trial.json'")
# Allow bounded extra CPU for real body/face compositing, while retaining all
# unique-frame and tail-latency gates and staying below the old uncapped load.
source=source.replace("baseline['cpu_percent']*1.05","baseline['cpu_percent']*1.25")
exec(compile(source,str(HERE/'trial_stable_fps.py'),'exec'))
