"""Same private Hub root and CPU models, new descriptive attribution routes."""
import contextlib,runpy,sys,traceback
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.dont_write_bytecode=True
with (H/'hub_stdout.log').open('a',encoding='utf-8',buffering=1) as out,(H/'hub_stderr.log').open('a',encoding='utf-8',buffering=1) as err:
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        try:runpy.run_path(str(A/'tools/device_hub.py'),run_name='__main__')
        except BaseException:traceback.print_exc();raise
