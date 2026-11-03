"""Read service identity and shared GPU residency; never unload other models."""
import http.client, json, shutil, socket, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
from common.voice_service_capabilities import require_current_voice,source_fingerprint

def get(port,path):
    address='192.168.50.1' if port in (8791,8792,8795) else '127.0.0.1'
    connection=http.client.HTTPConnection(address,port,timeout=8)
    try:
        connection.request('GET',path);response=connection.getresponse()
        return response.status,json.loads(response.read())
    finally:connection.close()

services={}
for port in (8791,8792):
    status,value=get(port,'/health');assert status==200
    services[str(port)]={'http_status':status,**{k:value[k] for k in (
        'ready','service_revision','source_fingerprint','capabilities','llm_model','voice_protocol') if k in value}}
from common.frontend_wire import PROTOCOL,send,receive
with socket.create_connection(('192.168.50.1',8795),timeout=3) as connection:
    send(connection,{'protocol':PROTOCOL,'kind':'health'});frontend,pcm=receive(connection,1)
assert not pcm and frontend.get('protocol')==PROTOCOL and frontend.get('ready') is True
services['8795']={'transport':'framed_tcp','protocol':frontend['protocol'],'ready':True}
require_current_voice(services['8792'],'aura-qwen3.8-27b-abliterated:iq4_xs',source_fingerprint(AURA))
resources={}
for port in (11434,11435):
    try:
        status,value=get(port,'/api/ps')
        resources[str(port)]={'http_status':status,'models':[{k:model.get(k) for k in (
            'name','size','size_vram','context_length','expires_at')} for model in value.get('models',[])]}
    except OSError as exc:resources[str(port)]={'error':type(exc).__name__+': '+str(exc)}
binary=shutil.which('nvidia-smi')
if binary:
    result=subprocess.run([binary,'--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
    resources['gpu']={'returncode':result.returncode,'csv':result.stdout.strip(),'columns':['name','used_MiB','total_MiB','gpu_percent']}
resources.update(checked_at_utc=datetime.now(timezone.utc).isoformat(),other_model_action='read only; no unload, process stop, configuration change or weight operation')
(HERE/'resource_snapshot.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2),encoding='utf-8')
report={'status':'PASS','services':services,'source_fingerprint':source_fingerprint(AURA),'checked_at_utc':resources['checked_at_utc']}
(HERE/'windows_health_final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report));print(json.dumps(resources))
