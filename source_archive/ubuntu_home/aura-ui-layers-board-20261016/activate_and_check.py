"""Apply this fixed release, then run its ordered native acceptance checks."""
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
commands=[['run_board.py','--source','board_apply_update.py','--phase','apply-fixed'],
          ['run_acceptance.py']]
for command in commands:
    process=subprocess.Popen([sys.executable,str(root/command[0]),*command[1:]],
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    for line in process.stdout:
        try:
            data=json.loads(line)
            if 'response' in data:
                response=data['response']
                data={'phase':'apply-fixed','status':response.get('status'),'evidence':data.get('evidence'),
                      'native_tests':response.get('native_tests'),'error':data.get('error')}
            print(json.dumps(data,ensure_ascii=False),flush=True)
        except ValueError:print(line.rstrip(),flush=True)
    code=process.wait()
    if code:raise SystemExit(code)
