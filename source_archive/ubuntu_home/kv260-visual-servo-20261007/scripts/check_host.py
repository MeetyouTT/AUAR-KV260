#!/usr/bin/env python3
"""Save exact-source host verification; all register I/O uses test doubles."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
out = root/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-host-tests')
out.mkdir()
sources = [root/name for name in ('vsrv_driver.py','vsrv_transport.py','face_servo_control.py','physical_motion_service.py','fixed_view_mapping.py','realtime_visual_servo.py','vision_core.py','motion_service.py','x11_window.py')]
sources += sorted((root/'tests').glob('test_*.py'))
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={str(p.relative_to(root)):digest(p) for p in sources}
for path in sources:
    saved=out/path.relative_to(root);saved.parent.mkdir(exist_ok=True);saved.write_bytes(path.read_bytes())
commands = [[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'],
            [sys.executable,'-m','py_compile']+[str(p) for p in sources]]
results=[]
for index,argv in enumerate(commands):
    result=subprocess.run(argv,cwd=root,text=True,capture_output=True,timeout=60)
    output=result.stdout+result.stderr
    (out/('command-%d.txt'%index)).write_text(output)
    results.append({'command':argv,'rc':result.returncode})
    print(output[-5000:])
    if result.returncode:break
log=(out/'command-0.txt').read_text()
count=re.search(r'Ran (\d+) tests',log)
passed=len(results)==2 and all(r['rc']==0 for r in results) and bool(count) and '\nOK\n' in log and all(digest(root/name)==sha for name,sha in hashes.items())
status={'passed':passed,'test_count':int(count.group(1)) if count else None,'evidence':str(out),
        'commands':results,'source_sha256':hashes,'board_accessed':False,'register_transport':'TEST_DOUBLE'}
data=json.dumps(status,indent=2)+'\n'
(out/'status.json').write_text(data);(root/'CURRENT_HOST_TESTS.json').write_text(data)
print(json.dumps({k:status[k] for k in ('passed','test_count','evidence','board_accessed')}))
raise SystemExit(0 if passed else 1)
