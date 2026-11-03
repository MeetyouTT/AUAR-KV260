import sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent))
import bootstrap
import os,tempfile,uuid,pytest
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
raise SystemExit(pytest.main(['-q',str(H/'test_startup_policy.py'),'--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp/'pytest')]))
