import bootstrap
bootstrap.service_module()
import os,sys,tempfile,uuid
from pathlib import Path
from unittest.mock import patch
import pytest
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
task_tmp=H/'test_tmp'/uuid.uuid4().hex;task_tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(task_tmp);tempfile.tempdir=str(task_tmp)
tests=['test_long_conversation.py','test_profile_memory.py','test_memory_controls.py','test_voice_channel.py','test_voice_service_health.py']
def no_production_hub(*a,**kw):raise OSError('Synthetic regression never calls production device memory')
with patch('tools.device_client.call',no_production_hub):
    result=pytest.main(['-q',str(H/'test_handoff.py'),str(H/'test_natural_memory.py'),str(H/'test_controls.py'),str(H/'test_timeline.py'),str(H/'test_summaries.py'),
       *[str(A/'tests/framework'/x) for x in tests],'--junitxml='+str(H/'tests.xml'),'--basetemp='+str(task_tmp/'pytest')]+sys.argv[1:])
raise SystemExit(result)

