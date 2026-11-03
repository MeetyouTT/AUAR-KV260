"""Retry unchanged candidate tests with the pan test helper import path."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text())
remote=r'''
import hashlib,json,os,subprocess
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
for n,sha in dict(c['files'],**c['preserved']).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
modules=['test_listening_timing','test_memory_controls','test_handsfree_dialogue','test_automatic_conversation',
 'test_long_conversation','test_voice_channel','test_board_avatar_worker','test_channel_jobs',
 'test_identity_capture_snapshot','test_spoken_identity_query','test_simple_enrollment','test_board_ui_services',
 'test_voice_latency','test_voice_barge_in','test_persistent_audio','test_gstreamer_audio','test_audio_capture',
 'test_manual_pan','test_manual_pan_process']
env=dict(os.environ,PYTHONPATH=str(root/'aura')+':'+str(root/'aura/tests/framework'),PYTHONDONTWRITEBYTECODE='1')
run=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*['tests/framework/'+n+'.py' for n in modules]],
 cwd=root/'aura',env=env,capture_output=True,text=True,timeout=160)
(stage/'tests_retry.log').write_text(run.stdout+run.stderr)
print(json.dumps({'passed':run.returncode==0,'output':run.stdout+run.stderr,'candidate_unchanged':True}))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=190));(HERE/'tests_retry.log').write_text(r['output'],encoding='utf-8')
if not (HERE/'candidate_initial_collection_failure.json').exists():
 (HERE/'candidate_initial_collection_failure.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
c.update(tests_passed=r['passed'],test_retry_reason='Pan process tests require tests/framework helper import path')
(HERE/'candidate.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
print(r['output']);assert r['passed'] and c['preflight_passed']
