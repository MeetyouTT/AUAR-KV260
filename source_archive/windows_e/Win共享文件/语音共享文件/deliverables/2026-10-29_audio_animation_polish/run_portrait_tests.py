import bootstrap
import os,sys,tempfile,uuid,pytest
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
raise SystemExit(pytest.main(['-q',str(A/'tests/framework/test_portrait_offload.py'),
 '--junitxml='+str(H/'portrait_tests.xml'),'--basetemp='+str(tmp/'pytest')]))
