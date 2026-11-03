"""Run the fixed deployed-UI checks sequentially; stop on any failed phase."""
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
phases=[('board_ready.py','ready-final'),('board_pages.py','native-pages'),
        ('board_native_recording.py','native-recording'),('board_playback_final.py','playback-final')]
for source,phase in phases:compile((root/source).read_bytes(),source,'exec')
for source,phase in phases:
  for attempt in range(1,4) if source=='board_ready.py' else range(1,2):
    current_phase=phase+'-'+str(attempt) if source=='board_ready.py' else phase
    observed_status=None
    process=subprocess.Popen([sys.executable,str(root/'run_board.py'),'--stage-helper',
                              '--source',source,'--phase',current_phase],stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,text=True)
    for line in process.stdout:
        try:
            data=json.loads(line)
            response=data.get('response',{})
            if response.get('status'):observed_status=response['status']
            print(json.dumps({'phase':current_phase,'step':data.get('step'),'evidence':data.get('evidence'),
                              'status':response.get('status'),'complete':data.get('complete'),
                              'error':data.get('error')},ensure_ascii=False),flush=True)
        except ValueError:print(line.rstrip(),flush=True)
    code=process.wait()
    if code:raise SystemExit(code)
    if source!='board_ready.py' or observed_status=='READY':break
  else:raise RuntimeError('GUI startup did not become ready after bounded checks')
