"""Start only missing wired model services; existing compatible services are reused."""
import argparse
import http.client
import json
from pathlib import Path
import socket
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--voice-python')
args=parser.parse_args()
voice=args.voice_python or json.loads((ROOT/'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json').read_text(encoding='utf-8'))['voice']['python']
if not Path(voice).is_file():raise SystemExit('Pass the actual accepted voice environment with --voice-python')
with socket.socket() as probe:probe.bind(('192.168.50.1',0))
started={}
for port,script,extra in (
    (8791,'asr_server.py',['--model-dir',str(ROOT/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14')]),
    (8792,'board_model_host.py',['--root',str(HERE/'model_host')])):
    with socket.socket() as probe:
        probe.settimeout(.5);listening=probe.connect_ex(('192.168.50.1',port))==0
    if listening:
        connection=http.client.HTTPConnection('192.168.50.1',port,timeout=3)
        try:
            connection.request('GET','/health');response=connection.getresponse();health=json.loads(response.read())
            expected='aura-asr-1' if port==8791 else 'aura-voice-1'
            actual=health.get('protocol') if port==8791 else health.get('voice_protocol')
            if response.status!=200 or actual!=expected or not health.get('ready'):
                raise SystemExit('Port occupied by an incompatible/not-ready service: '+str(port))
        finally:connection.close()
        started[str(port)]={'reused':True};continue
    with (HERE/f'port_{port}_stdout.log').open('a',encoding='utf-8') as output, (HERE/f'port_{port}_stderr.log').open('a',encoding='utf-8') as error:
        process=subprocess.Popen([voice,'-B','-u',str(ROOT/'aura/tools'/script),'--listen','192.168.50.1',
                                  '--port',str(port),*extra],cwd=ROOT/'aura',stdout=output,stderr=error,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    started[str(port)]={'pid':process.pid,'ready_not_yet_verified':True}
(HERE/'models_launch.json').write_text(json.dumps(started,indent=2),encoding='utf-8')
print(json.dumps(started))
