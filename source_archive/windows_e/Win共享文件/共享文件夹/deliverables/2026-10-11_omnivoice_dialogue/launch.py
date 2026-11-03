"""Launch the local real-dialogue stage; keep child logs and no console windows."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import webbrowser

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--ui-python',default=str(ROOT/'.venv-live/Scripts/python.exe'))
parser.add_argument('--voice-python')
parser.add_argument('--model-path')
parser.add_argument('--llm-model',default='qwen3:4b-instruct-2507-q4_K_M')
args=parser.parse_args()
config=json.loads((HERE/'stage_config.json').read_text(encoding='utf-8'))
if args.voice_python:
    config['voice']['python']=args.voice_python;config['microphone']['python']=args.voice_python
if args.model_path:config['voice']['model_path']=args.model_path
config['voice']['model_path']=config['voice']['model_path'].replace('${PROJECT_ROOT}',str(ROOT))
for python in (args.ui_python,config['voice']['python'],config['microphone']['python']):
    if not Path(python).is_file():raise SystemExit('Python missing; pass machine paths: '+python)
if not Path(config['voice']['model_path']).is_dir():raise SystemExit('OmniVoice model directory missing')
local=HERE/'machine_config.json';local.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
def listening(port):
    with socket.socket() as sock:
        sock.settimeout(1);return sock.connect_ex(('127.0.0.1',port))==0
def start(name,command):
    with (HERE/(name+'.log')).open('a',encoding='utf-8') as log:
        return subprocess.Popen(command,stdout=log,stderr=log,cwd=ROOT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).pid
processes={}
if not listening(config['dialogue']['port']):
    processes['host']=start('dialogue_host',[sys.executable,'-B','-u',str(ROOT/'aura/tools/dialogue_host_ollama.py'),
        '--port',str(config['dialogue']['port']),'--backend','ollama','--model',args.llm_model,'--strict','--fast'])
if not listening(config['browser_port']):
    processes['stage']=start('stage',[args.ui_python,'-B','-u',str(ROOT/'aura/tools/realtime_stage.py'),
        '--root',str(HERE),'--config',str(local),'--browser-only'])
(HERE/'last_launch.json').write_text(json.dumps(processes,indent=2),encoding='utf-8')
url='http://127.0.0.1:'+str(config['browser_port'])+'/'
print('Open after initialization: '+url)
webbrowser.open(url)
