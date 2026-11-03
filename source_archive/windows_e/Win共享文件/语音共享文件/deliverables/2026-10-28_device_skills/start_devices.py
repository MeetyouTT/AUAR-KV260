"""Start the shared speaker/memory Hub; generic Qwen-VL inference is retired."""
import json,socket,subprocess,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
def occupied(port):
    with socket.socket() as s:return s.connect_ex(('127.0.0.1',port))==0
def health(port,path='/health'):
    with urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
def spawn(name,cmd):
    with (HERE/(name+'.stdout.log')).open('ab') as out,(HERE/(name+'.stderr.log')).open('ab') as err:
        p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS)
    (HERE/(name+'_process.json')).write_text(json.dumps({'pid':p.pid,'command':cmd},indent=2),encoding='utf-8')
    return p
if not occupied(8812):
    spawn('hub',[r'D:\AIModels\speaker-identity\venv\Scripts\python.exe','-B',str(HERE/'launch_hub.py'),
        '--root',str(Path.home()/'AppData/Local/Aura/device-memory'),
        '--speaker-model',r'D:\AIModels\speaker-identity\ecapa'])
else:
    assert health(8812).get('revision')=='device-timeline-v2','Unknown device hub; preserve it'
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    try:
        h=health(8812)
        if h.get('speaker_ready'):
            (HERE/'devices_health.json').write_text(json.dumps({'visual':{'enabled':False,'reason':'semantic_vision_removed'},'hub':h},indent=2));print(json.dumps(h));break
    except (OSError,ValueError):pass
    time.sleep(.5)
else:raise TimeoutError('Device services not ready; inspect logs before retrying')
