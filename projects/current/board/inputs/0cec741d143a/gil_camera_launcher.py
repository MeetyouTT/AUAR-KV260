"""Experimental process-local interpreter interval around the pinned entrypoint."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

CAMERA_SHA='1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
ALLOWED_ROOT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')


def launch(argv,*,allowed_root=ALLOWED_ROOT,expected_sha=CAMERA_SHA,
           record_directory=None,runner=runpy.run_path):
    selected=os.environ.get('AURA_EXPERIMENT_GIL_MS')
    if selected not in ('1','5'):raise ValueError('Explicit 1ms or 5ms experiment required')
    if not argv:raise ValueError('Pinned camera entrypoint required')
    target=Path(argv[0])
    if (not target.is_absolute() or target.resolve(strict=True)!=target
            or allowed_root.resolve() not in target.parents or target.name!='board_camera_motion.py'
            or hashlib.sha256(target.read_bytes()).hexdigest()!=expected_sha):
        raise ValueError('Camera entrypoint differs from pinned experiment')
    record_directory=Path(record_directory) if record_directory is not None else Path(__file__).parent
    old_interval=sys.getswitchinterval();old_argv=sys.argv
    try:
        sys.setswitchinterval(int(selected)/1000.)
        actual=sys.getswitchinterval()
        if abs(actual-int(selected)/1000.)>1e-9:raise RuntimeError('Interpreter interval was not applied')
        record={'pid':os.getpid(),'requested_ms':int(selected),'actual_start_seconds':actual,
            'previous_seconds':old_interval,'target':str(target),'target_sha256':expected_sha,
            'scope':'interpreter startup setting in this camera process only; not OS timeslice or hardware deadline'}
        with (record_directory/('process-setting-'+str(os.getpid())+'.json')).open('x') as f:
            json.dump(record,f)
        sys.argv=list(argv)
        return runner(str(target),run_name='__main__')
    finally:
        sys.argv=old_argv;sys.setswitchinterval(old_interval)


if __name__=='__main__':launch(sys.argv[1:])
