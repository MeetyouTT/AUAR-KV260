"""Detached WMI worker with an OS process-lifetime lock for each role."""
import datetime,json,os,runpy,subprocess,sys,traceback,uuid
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
role=sys.argv[1] if len(sys.argv)==2 else ''
targets={'deploy':OUT/'deploy_5090.py','download':OUT/'download_llm_ranges.py',
    'ollama':ROOT/'deliverables/2026-10-18_board_dialogue/project_ollama.py'}
if role not in targets:raise SystemExit('Known worker role required')
sys.path[:0]=[str(ROOT/'aura'),str(targets[role].parent)]
os.environ['PATH']='D:/LLM/Ollama'+os.pathsep+os.environ.get('PATH','')
from tools.service_instance_lock import ServiceInstanceLock,ServiceAlreadyRunning
log=OUT/(role+'_wmi_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.log')
sys.stdout=log.open('a',encoding='utf-8',buffering=1);sys.stderr=sys.stdout
try:
    with ServiceInstanceLock(OUT/(role+'.instance.lock')):
        query="[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$p=Get-CimInstance Win32_Process -Filter 'ProcessId="+str(os.getpid())+"';[pscustomobject]@{pid=[int]$p.ProcessId;created_utc=$p.CreationDate.ToUniversalTime().ToString('o');executable=$p.ExecutablePath}|ConvertTo-Json -Compress"
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',query],capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise RuntimeError('Worker identity unavailable')
        record=json.loads(result.stdout.decode('utf-8-sig'))
        record.update(role=role,entry_wrapper=str(Path(__file__).resolve()),script=str(targets[role]),
            log=str(log),creation='independent hidden Win32_Process.Create',one_time=True)
        name={'deploy':'deployment_owner.json','download':'download_owner.json','ollama':'ollama_worker_owner.json'}[role]
        p=OUT/name
        if p.exists():p.replace(OUT/(p.stem+'.before-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+'-'+uuid.uuid4().hex[:6]+'.json'))
        p.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'status':'RUNNING','role':role,'pid':os.getpid()},ensure_ascii=False),flush=True)
        runpy.run_path(str(targets[role]),run_name='__main__')
except ServiceAlreadyRunning:
    print(json.dumps({'status':'ALREADY_RUNNING','role':role}),flush=True)
except BaseException:
    traceback.print_exc();raise
