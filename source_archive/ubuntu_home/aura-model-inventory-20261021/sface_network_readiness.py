import json,socket,subprocess,urllib.request
from pathlib import Path
out={'scope':'READ_ONLY_NETWORK_READINESS_NO_MODEL_OR_AUDIO_REQUESTS','ethernet':{}}
for n in ['operstate','carrier']:
    try:out['ethernet'][n]=Path('/sys/class/net/eth0'/Path(n)).read_text().strip()
    except OSError:out['ethernet'][n]=None
try:
    raw=subprocess.check_output(['ip','-j','route','get','192.168.50.1'],timeout=3)
    out['route']=[{k:v for k,v in item.items() if k in ('dst','gateway','dev','prefsrc','type')} for item in json.loads(raw)]
except Exception as e:out['route_error']=type(e).__name__
try:
    with socket.create_connection(('192.168.50.1',8792),timeout=2):out['tcp_8792']='connected'
except OSError as e:out['tcp_8792']={'error':type(e).__name__,'errno':e.errno,'reason':str(e)}
try:
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://192.168.50.1:8792/health',timeout=2) as r:s=json.load(r)
    out['health']={'reachable':True,'top_keys':list(s)[:30]}
except Exception as e:out['health']={'reachable':False,'error':type(e).__name__,'reason':str(getattr(e,'reason',e))}
print(json.dumps(out))
