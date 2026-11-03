"""Run compatible Windows speech and identity-query regression tests."""
import os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
modules=('test_spoken_identity_query','test_spoken_input','test_voice_enrollment',
 'test_simple_enrollment','test_sampling_voice','test_channel_jobs','test_voice_channel',
 'test_history_reuse','test_face_features')
result=subprocess.run([sys.executable,'-B','-m','pytest','-q','-k','not BoardSimpleFlowTests',
 *['tests/framework/'+name+'.py' for name in modules]],cwd=ROOT/'aura',
 env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
previous=HERE/'tests_pc.log'
if previous.exists() and not (HERE/'tests_pc_linux_only_initial.log').exists():
    previous.rename(HERE/'tests_pc_linux_only_initial.log')
previous.write_text(result.stdout+result.stderr,encoding='utf-8')
print(result.stdout+result.stderr,end='')
sys.exit(result.returncode)
