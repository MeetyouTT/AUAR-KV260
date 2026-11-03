"""Start only the isolated CPU visual backend; keep all existing models."""
import json,subprocess,socket,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
manifest=json.loads((HERE/'vlm_model_manifest.json').read_text(encoding='utf-8'))
model=manifest['files']['Qwen3VL-2B-Instruct-Q4_K_M.gguf']['path']
projector=manifest['files']['mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf']['path']
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1',8810))==0:raise RuntimeError('Port 8810 already occupied; inspect ownership before reusing')
cmd=[r'C:\Users\35870\AppData\Local\Programs\Ollama\lib\ollama\llama-server.exe',
    '--model',model,'--mmproj',projector,'--alias','aura-vision','--host','127.0.0.1','--port','8810',
    '--device','none','--n-gpu-layers','0','--no-mmproj-offload','--threads','2','--threads-batch','2',
    '--ctx-size','2048','--parallel','1','--image-max-tokens','512']
with (HERE/'vlm_server.stdout.log').open('ab') as out,(HERE/'vlm_server.stderr.log').open('ab') as err:
    process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS)
(HERE/'vlm_process.json').write_text(json.dumps({'pid':process.pid,'command':cmd,'purpose':'isolated visual question CPU validation'},indent=2),encoding='utf-8')
deadline=time.monotonic()+45
while time.monotonic()<deadline:
    if process.poll() is not None:raise RuntimeError('VLM exited: '+str(process.returncode))
    try:
        with urllib.request.urlopen('http://127.0.0.1:8810/health',timeout=2) as r:value=json.load(r)
        if value.get('status')=='ok':print(json.dumps({'pid':process.pid,'ready':True,'gpu_layers':0}));break
    except (OSError,ValueError):pass
    time.sleep(.5)
else:raise TimeoutError('VLM still initializing; inspect before restarting')

