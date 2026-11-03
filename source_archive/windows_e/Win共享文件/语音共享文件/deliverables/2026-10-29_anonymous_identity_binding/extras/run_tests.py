import bootstrap
import os,sys,tempfile,uuid,pytest
from pathlib import Path
H=Path(__file__).resolve().parent;tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
raise SystemExit(pytest.main(['-q',str(H/'test_hub_binding.py'),'--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp/'pytest')]+sys.argv[1:]))
