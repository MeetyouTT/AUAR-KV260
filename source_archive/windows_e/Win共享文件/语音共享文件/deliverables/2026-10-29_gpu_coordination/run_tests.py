import bootstrap
import os,sys,tempfile,uuid,pytest
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
names=('test_voice_channel.py','test_voice_worker_lifecycle.py','test_voice_service_health.py',
       'test_voice_latency.py','test_first_sentence_latency.py')
raise SystemExit(pytest.main(['-q',str(H/'test_gpu_coordination.py'),str(H/'test_tts_cold_lifecycle.py'),*[str(A/'tests/framework'/name) for name in names],
 '--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp/'pytest')]))
