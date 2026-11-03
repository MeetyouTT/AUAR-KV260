"""Run the three fixed, reviewed GUI acceptance phases in dependency order."""
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
phases=[('board_ready.py','ui-ready'),('board_native_recording.py','native-recording'),
        ('board_auto_limit.py','auto-limit')]
for source,phase in phases:
    compile((root/source).read_bytes(),source,'exec')
for source,phase in phases:
    process=subprocess.Popen([sys.executable,str(root/'run_board.py'),'--stage-helper',
        '--source',source,'--phase',phase],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    for line in process.stdout:
        try:
            value=json.loads(line)
            response=value.get('response',{})
            small={'phase':phase,'evidence':value.get('evidence'),'step':value.get('step'),
                   'status':response.get('status'),'complete':value.get('complete'),'error':value.get('error')}
            print(json.dumps(small),flush=True)
        except ValueError:
            print(line.rstrip(),flush=True)
    rc=process.wait()
    if rc:raise SystemExit(rc)
