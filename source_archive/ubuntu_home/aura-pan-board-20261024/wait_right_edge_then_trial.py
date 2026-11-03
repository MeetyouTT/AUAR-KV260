"""Wait read-only for the actual right-edge face, then one visible finite session."""
import hashlib,json,runpy,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[];matched=False;start=time.monotonic()
while time.monotonic()-start<35:
 with o.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=2) as response:p=json.load(response)
 if p.get('state')=='READY':
  x,y,w,h=p['target']['box'];margin=(p['frame_width']-x-w)/p['frame_width'];rows.append(round(margin,4))
  if margin<=.08 and min(w,h)>=48:matched=True;break
 time.sleep(.08)
if not matched:
 print(json.dumps({'status':'WAITED_FOR_RIGHT_EDGE_NO_ACTUATION','elapsed_s':round(time.monotonic()-start,3),'right_margin_min':min(rows) if rows else None,'ready_observations':len(rows),'ARM_sent':False,'COMMIT_sent':False}))
else:
 path=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/helpers/start-face-ui-trial.py')
 assert hashlib.sha256(path.read_bytes()).hexdigest()=='ebc2f46c9bd1be6624ce3e6c3fe6997473ea558fb8e94315f2aeaef51390cb58'
 runpy.run_path(str(path),run_name='__main__')
