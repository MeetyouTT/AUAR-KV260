import importlib,os,sys,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path[:0]=[str(A),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
for name in ('common','tools','board','board.runtime','board.runtime.audio'):
    package=importlib.import_module(name);directory=H/'candidate'/name.replace('.','/')
    package.__path__=[str(directory),str(A/name.replace('.','/'))]
tmp=H/'test_tmp';tmp.mkdir(exist_ok=True)
os.environ['TMP']=os.environ['TEMP']=str(tmp);tempfile.tempdir=str(tmp)
