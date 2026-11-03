import bootstrap
import os,sys,tempfile,uuid,pytest
from pathlib import Path
H=Path(__file__).resolve().parent;tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
sys.path.insert(0,str(H.parent/'2026-10-29_speaker_visual_cooperation'))
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
raise SystemExit(pytest.main(['-q',str(H/'test_identity_binding.py'),'--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp/'pytest')]+sys.argv[1:]))
