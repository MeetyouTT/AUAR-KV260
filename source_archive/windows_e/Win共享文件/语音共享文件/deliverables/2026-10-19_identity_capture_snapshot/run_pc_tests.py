import os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
modules=('test_identity_capture_snapshot','test_board_ui_services','test_spoken_identity_query','test_spoken_input','test_voice_enrollment',
 'test_simple_enrollment','test_sampling_voice','test_channel_jobs','test_voice_channel',
 'test_history_reuse','test_face_features','test_enrollment_photos')
r=subprocess.run([sys.executable,'-B','-m','pytest','-q','-k',
 'not BoardSimpleFlowTests and not PhotoArchiveIntegrationTests and not test_connections_persist_without_changing_audio_preferences',
 *['tests/framework/'+n+'.py' for n in modules],
 'tests/framework/test_enrollment_sampling.py::SamplingTests'],cwd=ROOT/'aura',
 env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
(HERE/'tests_pc.log').write_text(r.stdout+r.stderr,encoding='utf-8');print(r.stdout+r.stderr,end='');sys.exit(r.returncode)
