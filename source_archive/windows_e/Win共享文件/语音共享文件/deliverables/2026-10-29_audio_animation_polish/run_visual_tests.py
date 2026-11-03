import visual_bootstrap
import os,sys,tempfile,uuid,pytest
from pathlib import Path
H=Path(__file__).resolve().parent
tmp=H/'test_tmp'/uuid.uuid4().hex;tmp.mkdir(parents=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
raise SystemExit(pytest.main(['-q',str(H/'test_visual_materials.py'),'--junitxml='+str(H/'visual_tests.xml'),
 '--basetemp='+str(tmp/'pytest')]+sys.argv[1:]))
