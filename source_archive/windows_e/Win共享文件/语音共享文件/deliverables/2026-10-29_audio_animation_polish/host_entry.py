"""Independent CPU-only portrait process with bounded owned logs."""
import contextlib,os,runpy,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path[:0]=[r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps',str(A)]
os.environ['OMP_NUM_THREADS']=os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
if __name__=='__main__':
    with (H/'host_stdout.log').open('a',encoding='utf-8',buffering=1) as out,(H/'host_stderr.log').open('a',encoding='utf-8',buffering=1) as err:
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):runpy.run_path(str(A/'tools/portrait_host.py'),run_name='__main__')
