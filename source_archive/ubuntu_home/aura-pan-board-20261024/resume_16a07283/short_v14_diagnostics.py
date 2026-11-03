import json,subprocess,time,urllib.request
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r12')
out=P/('input-short-'+str(time.monotonic_ns())+'.json')
code="import faulthandler,runpy,sys;faulthandler.dump_traceback_later(12);sys.path.insert(0,"+repr(str(P))+");runpy.run_path("+repr(str(P/'run_input_diagnostics.py'))+",run_name='__main__')"
args=['/usr/bin/python3','-B','-c',code,'--settings','/home/root/aura-pan-current-20261024/16a07283/face-zone-settings.json','--output',str(out),'--duration','8']
try:
 r=subprocess.run(args,capture_output=True,text=True,timeout=18)
 print(json.dumps({'returncode':r.returncode,'stderr':r.stderr[-4000:],'diagnostics':json.loads(out.read_text()) if out.stat().st_size else None,'output':str(out)}))
except subprocess.TimeoutExpired as e:
 print(json.dumps({'status':'DIAGNOSTIC_TIMEOUT','stderr':(e.stderr or b'').decode()[-5000:],'output_bytes':out.stat().st_size}))
