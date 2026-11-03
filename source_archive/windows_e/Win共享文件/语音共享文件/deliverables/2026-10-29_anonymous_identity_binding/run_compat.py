import bootstrap
import os,sys,tempfile,uuid,pytest
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent/'2026-10-29_speaker_visual_cooperation'
sys.path.insert(0,str(B));tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
tests=['test_speaker_visual.py','test_turn_attribution_store.py','test_speaker_analysis.py','test_speaker_recorder.py','test_device_attribution_routes.py','test_pcm_lifecycle.py']
raise SystemExit(pytest.main(['-q',*[str(B/name) for name in tests],
 '--junitxml='+str(H/'compat_tests.xml'),'--basetemp='+str(tmp/'pytest')]+sys.argv[1:]))
