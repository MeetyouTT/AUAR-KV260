"""Read-only model/service/resource snapshot; never generates speech or photos."""
import argparse, concurrent.futures, json, re, subprocess, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output',default='status.json')
args=parser.parse_args()
if Path(args.output).name!=args.output or not args.output.endswith('.json'):
    parser.error('--output must be a JSON filename in the report directory')
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def get(url, body=None):
    request=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)

cfg=json.loads((ROOT/'aura/config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
storage=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))
report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'configured_dialogue':cfg,'storage':storage,
 'read_only':True,'generation_requested':False,'photos_captured':False,'models_loaded_by_audit':False}
queries={'asr':('http://192.168.50.1:8791/health',None),'voice':('http://192.168.50.1:8792/health',None),
 'ollama_ps':(cfg['ollama_host']+'/api/ps',None),'model_metadata':(cfg['ollama_host']+'/api/show',{'model':cfg['model']})}
remote=r'''
import json,subprocess,urllib.request
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
health=get(8790,'/health');state=get(8790,'/v1/ui/status');ui=get(8783,'/api/state')
argv=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
camera_path=Path(argv[argv.index('--config')+1]);identity_path=Path(json.loads(camera_path.read_text())['identity']['config'])
config=json.loads(identity_path.read_text());identity=state['modules'].get('identity',{})
turns=[]
for turn in ui.get('turns',[])[-5:]:
 metrics=turn.get('server_metrics',{});timing=metrics.get('timing',{});llm=timing.get('llm',{})
 turns.append({'generation':turn.get('generation'),'audio_complete':turn.get('audio_complete'),
  'software_request_to_answer_seconds':turn.get('request_to_answer_seconds'),
  'first_pcm_ms':metrics.get('first_pcm_ms'),'llm_backend':llm.get('backend'),'tts_cache_hits':metrics.get('tts_cache_hits')})
memory={}
for line in Path('/proc/meminfo').read_text().splitlines():
 key,raw=line.split(':',1)
 if key in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):memory[key+'_KiB']=int(raw.split()[0])
services={name:subprocess.run(['systemctl','is-active',name],capture_output=True,text=True,timeout=4).stdout.strip()
 for name in ('aura-camera-ui.service','aura-avatar-ui.service')}
print(json.dumps({'camera':health,'identity':{'state':identity.get('state'),'database_revision':identity.get('db_version'),
 'registered_count':len(identity.get('people',[])),'detail':identity.get('detail') if identity.get('state')!='KNOWN' else 'KNOWN_NAME_REDACTED',
 'threshold':config['threshold'],'ambiguity_margin':config['ambiguity_margin'],'result_ttl_ms':config['result_ttl_ms'],
 'model_id':config['model_id'],'face_model':config['face_model'],'embedding_model':config['embedding_model']},
 'ui':{'phase':ui.get('phase'),'automatic':ui.get('automatic_conversation'),'recent_turn_metrics':turns},
 'services':services,'memory':memory,'load_average':Path('/proc/loadavg').read_text().strip(),
 'names_exported':False,'templates_exported':False,'photos_captured':False}))
'''
def board():return json.loads(ssh('python3 -B -',remote,timeout=25))
def gpu():
    run=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu',
        '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8)
    return {'returncode':run.returncode,'csv_columns':['name','total_MiB','used_MiB','free_MiB','utilization_percent','temperature_C'],
        'output':run.stdout.strip(),'error':run.stderr.strip()}
def host_processes():
    script=r'''
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()
$taskListeners=@(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in @(8791,8792,11435)} | Select-Object LocalAddress,LocalPort,OwningProcess -Unique)
$taskOwners=@($taskListeners | Select-Object -ExpandProperty OwningProcess -Unique)
$taskAll=@(Get-CimInstance Win32_Process)
$taskDescendants=@($taskOwners)
1..3 | ForEach-Object {$taskDescendants=@($taskDescendants)+@($taskAll | Where-Object {$_.ParentProcessId -in $taskDescendants} | Select-Object -ExpandProperty ProcessId) | Select-Object -Unique}
$taskRows=@($taskAll | Where-Object {$_.ProcessId -in $taskDescendants} | ForEach-Object {
 $taskRunnerPort=$null
 if ($_.Name -ieq 'llama-server.exe' -and $_.CommandLine -match '--port\s+(\d+)') {$taskRunnerPort=[int]$Matches[1]}
 [pscustomobject]@{pid=$_.ProcessId;parent_pid=$_.ParentProcessId;name=$_.Name;working_set_bytes=$_.WorkingSetSize;runner_port=$taskRunnerPort}
})
$taskOS=Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{listeners=$taskListeners;processes=$taskRows;memory_total_KiB=$taskOS.TotalVisibleMemorySize;memory_free_KiB=$taskOS.FreePhysicalMemory} | ConvertTo-Json -Depth 6 -Compress
'''
    run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,
        encoding='utf-8',errors='replace',timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if run.returncode:raise RuntimeError(run.stderr.strip())
    return json.loads(run.stdout.lstrip('\ufeff'))

with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
    jobs={pool.submit(get,*args):name for name,args in queries.items()}
    jobs.update({pool.submit(board):'board',pool.submit(gpu):'gpu',pool.submit(host_processes):'host'})
    for future,name in jobs.items():
        try:report[name]=future.result()
        except Exception as exc:report[name]={'error':type(exc).__name__+': '+str(exc)}
metadata=report.get('model_metadata',{})
if 'error' not in metadata:
    info=metadata.get('model_info',{});match=re.search(r'^FROM\s+(.+)$',metadata.get('modelfile',''),re.M)
    report['model_metadata']={'details':metadata.get('details'),'parameters':metadata.get('parameters'),
      'parameter_count':info.get('general.parameter_count'),'architecture':info.get('general.architecture'),
      'actual_weight_source':match[1].strip() if match else None}
native=[]
for process in report.get('host',{}).get('processes',[]):
    if not process.get('runner_port'):continue
    base='http://127.0.0.1:'+str(process['runner_port'])
    try:
        props=get(base+'/props')
        native.append({'pid':process['pid'],'health':get(base+'/health'),'model_path':props.get('model_path'),
          'build_info':props.get('build_info'),'context':props.get('default_generation_settings',{}).get('n_ctx'),
          'total_slots':props.get('total_slots')})
    except Exception as exc:native.append({'pid':process['pid'],'error':str(exc)})
report['native_runners']=native
(HERE/args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
