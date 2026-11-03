"""Start isolated CPU services only; never unload or terminate other models."""
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
manifest=json.loads((HERE.parent/'2026-10-28_interaction_completion/vlm_model_manifest.json').read_text())
model=manifest['files']['Qwen3VL-2B-Instruct-Q4_K_M.gguf']['path']
projector=manifest['files']['mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf']['path']
if not occupied(8810):
    spawn('visual',[r'C:\Users\35870\AppData\Local\Programs\Ollama\lib\ollama\llama-server.exe',
        '--model',model,'--mmproj',projector,'--alias','aura-vision','--host','127.0.0.1','--port','8810',
        '--device','none','--n-gpu-layers','0','--no-mmproj-offload','--threads','2','--threads-batch','2',
        '--ctx-size','2048','--parallel','1','--image-max-tokens','512'])
else:
    props=health(8810,'/props')
    assert props.get('model_path')==model, 'Occupied VLM endpoint differs from expected model; preserve it'
if not occupied(8812):
    spawn('hub',[r'D:\AIModels\speaker-identity\venv\Scripts\python.exe','-B',str(HERE/'launch_hub.py'),
        '--root',str(Path.home()/'AppData/Local/Aura/device-memory'),
        '--speaker-model',r'D:\AIModels\speaker-identity\ecapa'])
else:
    assert health(8812).get('revision')=='device-timeline-v2','Unknown device hub; preserve it'
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    try:
        v=health(8810);h=health(8812)
        if v.get('status')=='ok' and h.get('speaker_ready'):
            (HERE/'devices_health.json').write_text(json.dumps({'visual':v,'hub':h},indent=2));print(json.dumps(h));break
    except (OSError,ValueError):pass
    time.sleep(.5)
else:raise TimeoutError('Device services not ready; inspect logs before retrying')
