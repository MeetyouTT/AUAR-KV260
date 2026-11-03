import bootstrap
bootstrap.service_module()
import os,sys,tempfile,uuid,pytest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';R=H.parent/'2026-10-29_chat_latency'
# Historical assertions are retained, but their loader now supplies the merged
# candidate rather than accidentally reloading their archived r9 implementation.
sys.modules['bootstrap_r9']=bootstrap
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
task_tests=['test_tts_idle_cache.py','test_timeline_intent.py','test_serialization.py','test_handoff.py',
 'test_natural_memory.py','test_controls.py','test_timeline.py','test_summaries.py']
framework=['test_long_conversation.py','test_profile_memory.py','test_memory_controls.py','test_voice_channel.py',
 'test_voice_service_health.py','test_first_sentence_latency.py','test_voice_worker_transport.py']
paths=[H/'test_parent_hooks.py',H/'test_legacy_budget.py',bootstrap.G/'test_gpu_coordination.py',*[R/name for name in task_tests],
 *[A/'tests/framework'/name for name in framework]]
paths=[p for p in paths if p.is_file()]
def offline_hub(*a,**kw):raise OSError('Synthetic regression never contacts production device service')
with patch('tools.device_client.call',offline_hub):
    result=pytest.main(['-q',*[str(p) for p in paths],'--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp/'pytest')])
raise SystemExit(result)
