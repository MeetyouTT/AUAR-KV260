"""Read-only network and longer SSH handshake check, without private user content."""
import json
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import KEY

def service(item):
    name,url=item
    try:
        value=json.load(urllib.request.urlopen(url,timeout=6))
        if name=='camera':
            result={k:value.get(k) for k in ('pid','camera_error','detector_error','capture_age_ms')}
            identity=value.get('identity',{})
            result.update(identity_ready=identity.get('ready'),photos=identity.get('enrollment_photos'))
        elif name=='ui':
            result={k:value.get(k) for k in ('phase','automatic_conversation','last_error')}
            result['voice_enrollment']=value.get('local_transcription',{}).get('service',{}).get('voice_enrollment')
        else:
            result={k:value.get(k) for k in ('ready','busy','llm_model','num_step')}
        return name,result
    except Exception as exc:
        return name,{'error':type(exc).__name__+': '+str(exc)}

with ThreadPoolExecutor() as pool:
    report=dict(pool.map(service,[('camera','http://192.168.50.2:8790/health'),
        ('ui','http://192.168.50.2:8783/api/state'),('pc','http://192.168.50.1:8792/health')]))
args=['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes',
      '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20',
      'root@192.168.50.2','true']
try:
    result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=25)
    report['ssh']={'exit_code':result.returncode,'error':result.stderr.strip()}
except subprocess.TimeoutExpired:
    report['ssh']={'error':'SSH handshake exceeded 25 seconds'}
(HERE/'connection_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
