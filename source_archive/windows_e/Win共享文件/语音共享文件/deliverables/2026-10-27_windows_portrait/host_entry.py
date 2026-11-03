"""Hidden independent CPU renderer entry with private-to-this-service logs."""
import contextlib,os,runpy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path[:0]=['C:/Users/35870/.codex/visualizations/2026/10/26/01a1772c-f263-75f1-bfa1-9bd865e5caa9/animation-fps-deps',str(AURA)]
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
if __name__=='__main__':
    with (HERE/'host_stdout.log').open('a',encoding='utf-8',buffering=1) as out,(HERE/'host_stderr.log').open('a',encoding='utf-8',buffering=1) as err:
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            runpy.run_path(str(AURA/'tools/portrait_host.py'),run_name='__main__')
