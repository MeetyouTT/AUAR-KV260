"""Run board-compatible regressions; Windows host HTTP is tested on Windows."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,os,subprocess
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
env=dict(os.environ,PYTHONPATH=str(root/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_simple_enrollment','test_enrollment_sampling','test_identity_face_targets','test_camera_identity','test_camera_ui_service','test_board_ui_services',
 'test_voice_enrollment_board','test_person_bytetrack','test_automatic_conversation','test_board_recording',
 'test_audio_capture','test_board_avatar_worker','test_transcription']
run=subprocess.run(['python3','-B','-m','unittest',*['tests.framework.'+n for n in modules],
 'tests.framework.test_face_features.FeatureProtocolTests','-v'],cwd=root/'aura',env=env,capture_output=True,text=True,timeout=90)
log=stage/'tests.log';log.rename(stage/'tests_initial_host_import_error.log');log.write_text(run.stdout+run.stderr)
c['tests_passed']=run.returncode==0;(stage/'candidate.json').write_text(json.dumps(c,indent=2))
print(json.dumps({'passed':run.returncode==0,'log':run.stdout+run.stderr}))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=120))
old=HERE/'tests_board.log';old.rename(HERE/'tests_initial_host_import_error.log')
old.write_text(r['log'],encoding='utf-8');c['tests_passed']=r['passed']
(HERE/'candidate.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print(r['log'][-300:]);assert r['passed']
