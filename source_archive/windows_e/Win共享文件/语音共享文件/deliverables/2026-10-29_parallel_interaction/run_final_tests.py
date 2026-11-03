import bootstrap_final as bootstrap
import os,sys,tempfile,uuid,pytest
import importlib
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;D=H.parent;A=H.parents[1]/'aura';R=D/'2026-10-29_chat_latency'
bootstrap.service_module()
sys.modules['bootstrap']=bootstrap;sys.modules['bootstrap_r9']=bootstrap;sys.modules['bootstrap_bridge']=bootstrap
for short in ('service_instance_lock','voice_startup_guard'):
    sys.modules[short]=importlib.import_module('tools.'+short)
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
task=['test_tts_idle_cache.py','test_timeline_intent.py','test_serialization.py','test_handoff.py',
      'test_natural_memory.py','test_controls.py','test_timeline.py','test_summaries.py']
framework=['test_long_conversation.py','test_profile_memory.py','test_memory_controls.py','test_voice_channel.py',
    'test_voice_service_health.py','test_first_sentence_latency.py','test_voice_worker_transport.py',
    'test_speaker_identity.py','test_spoken_identity_query.py']
speaker=['test_speaker_visual.py','test_turn_attribution_store.py','test_speaker_analysis.py','test_speaker_recorder.py',
    'test_device_attribution_routes.py','test_pcm_lifecycle.py','test_native_channel_jobs.py']
N=D/'2026-10-29_anonymous_identity_binding';S=D/'2026-10-29_speaker_visual_cooperation'
paths=[H/'test_parent_hooks.py',H/'test_legacy_budget.py',H/'test_final_host_integration.py',
    bootstrap.G/'test_gpu_coordination.py',*[R/name for name in task],*[A/'tests/framework'/name for name in framework],
    *[S/name for name in speaker],N/'test_identity_binding.py',N/'extras/test_hub_binding.py',S/'board_bridge/test_face_bridge.py']
startup=D/'2026-10-29_conversation_research/extras/startup_guard'
paths.extend(sorted(startup.glob('tests/test*.py')))
paths=[p for p in paths if p.is_file()]
def offline_hub(*a,**kw):raise OSError('Regression cannot contact production device service')
with patch('tools.device_client.call',offline_hub):
    result=pytest.main(['-q',*[str(p) for p in paths],'--junitxml='+str(H/'final_tests.xml'),'--basetemp='+str(tmp/'pytest')])
raise SystemExit(result)
