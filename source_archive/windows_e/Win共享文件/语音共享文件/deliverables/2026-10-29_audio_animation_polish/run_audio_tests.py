import bootstrap
from pathlib import Path
import os,sys,tempfile,uuid,pytest
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
tests=['test_persistent_audio.py','test_gstreamer_audio.py','test_voice_barge_in.py','test_barge_verification.py','test_channel_jobs.py']
raise SystemExit(pytest.main(['-q',str(H/'test_audio_flow.py'),*[str(H/'effective_tests/tests/framework'/name) for name in tests],
 '--junitxml='+str(H/'audio_tests_verified.xml'),'--basetemp='+str(tmp/'pytest')]+sys.argv[1:]))
