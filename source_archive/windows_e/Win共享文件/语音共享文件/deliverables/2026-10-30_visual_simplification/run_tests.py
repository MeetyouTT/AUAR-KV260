"""Production-source regression; all model and device dependencies are synthetic."""
import os,sys,tempfile,uuid,types
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path[:0]=[str(A),str(H),str(H.parent/'2026-10-29_anonymous_identity_binding'),
               str(H.parent/'2026-10-29_speaker_visual_cooperation')]
import pytest
# Historical tests import a bootstrap that otherwise prepends obsolete candidate
# sources. Keep every module in this run bound to the current production tree.
sys.modules['bootstrap']=types.ModuleType('bootstrap')
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
names=['test_long_conversation.py','test_profile_memory.py','test_memory_controls.py',
       'test_voice_channel.py','test_voice_service_health.py','test_first_sentence_latency.py',
       'test_speaker_identity.py','test_spoken_identity_query.py']
paths=[H/'test_retirement.py',*[A/'tests/framework'/name for name in names]]
D=H.parent
paths += [D/'2026-10-29_speaker_visual_cooperation/test_device_attribution_routes.py',
          D/'2026-10-29_anonymous_identity_binding/extras/test_hub_binding.py']
def offline(*a,**kw):raise OSError('Regression cannot contact production services')
with patch('tools.device_client.call',offline):
    code=pytest.main(['-q',*[str(p) for p in paths],'--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp/'pytest')])
raise SystemExit(code)
