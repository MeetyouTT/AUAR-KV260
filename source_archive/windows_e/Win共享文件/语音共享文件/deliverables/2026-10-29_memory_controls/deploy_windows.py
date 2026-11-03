"""Deploy the tested Windows-only memory candidate. Never restart board/hub/models."""
import ast,datetime,hashlib,json,shutil,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
assert plan['status']=='READY_WINDOWS_ONLY' and plan['tests_passed']==210
assert not (H/'deployment.json').exists(),'Inspect the existing deployment receipt'
receipt={'status':'PREPARING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'authority':'Windows','board_migration':False,'board_ui_restarted':False,'camera_restarted':False,
 'other_models_stopped':False,'hub_restarted':False,'files':plan['files'],'applied':[],
 'preserved_parallel_change':plan.get('preserved_parallel_change')}
def save():(H/'deployment.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def ps(args,timeout=30):
    r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*args],capture_output=True,timeout=timeout)
    if r.returncode:
        (H/'launcher_error.log').write_bytes(r.stdout+r.stderr)
        raise RuntimeError((r.stdout+r.stderr).decode('utf-8',errors='replace')[-700:])
    return r.stdout.decode('utf-8-sig',errors='replace')
def health():
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4) as r:return json.load(r)
def owners(stop=False):
    return json.loads(ps(['-File',str(H/'manage_owned.ps1'),'-Group','voice']+(['-Stop'] if stop else [])))
def gate():
    tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
    script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
    current=json.loads(ssh('python3 -B -',script,timeout=20))
    assert current['preflight_ready']
    for name in ('boot','actual_runtime','actual_config','config_sha256','pins','settings','pan'):
        assert current[name]==baseline[name],'Concurrent board change: '+name
    for name in ('camera_service','ui_service'):
        for key in ('MainPID','ExecStart','NRestarts','ActiveState'):assert current[name][key]==baseline[name][key]
    return {'boot':current['boot'],'runtime':current['actual_runtime'],'pins':len(current['pins']),
        'camera_pid':current['camera_service']['MainPID'],'ui_pid':current['ui_service']['MainPID'],
        'pan':current['pan'],'listening':current['listening'],'microphone_open':current['microphone_open']}
def models():
    command="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); @(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'ollama*' -or $_.Name -eq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,Name) | ConvertTo-Json -Compress"
    r=json.loads(ps(['-Command',command]));return r if isinstance(r,list) else [r]
def listeners():
    return json.loads(ps(['-Command',"[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); @(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in @(8791,8795,8796,8810,8812,11435)} | Select-Object LocalAddress,LocalPort,OwningProcess | Sort-Object LocalPort,LocalAddress) | ConvertTo-Json -Compress"]))
def checkpoint(phase):
    token=uuid.uuid4().hex;ps(['-File',str(H/'start_checkpoint.ps1'),'-Job',token,'-Phase',phase])
    path=H/('db_checkpoint_'+token+'.json');until=time.monotonic()+25
    while time.monotonic()<until and not path.exists():time.sleep(.2)
    value=json.loads(path.read_text(encoding='utf-8'));assert value['status']=='PASS',value.get('error')
    return value
def start():
    value=ps(['-File',str(H.parent/'2026-10-18_board_dialogue/start_background_models.ps1')],timeout=450)
    (H/'voice_restart.log').write_text(value,encoding='utf-8');return health()
try:
    first=health();assert first['ready'] and not first['busy']
    assert first['source_fingerprint']==plan['production_fingerprint'] and first['latency_options']['compact_grammar'] is False
    receipt['guard']=gate();time.sleep(.25);gate()
    assert hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()==plan['preserved_latency_sha256']
    for name,entry in plan['files'].items():
        path=A/name
        assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)==entry['before'],name
        assert hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()==entry['candidate'],name
    receipt['other_listeners']=listeners();receipt['models_before']=models();receipt['owner_before']=owners();save()
    receipt['stop_voice']=owners(True);receipt['checkpoint_before']=checkpoint('before');save()
    for name,entry in plan['files'].items():
        path=A/name
        assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)==entry['before'],name
        shutil.copy2(H/'candidate_source'/name,path);receipt['applied'].append(name);save()
    receipt['status']='STARTING';save()
    voice=start()
    assert voice['ready'] and voice['service_revision']==plan['candidate_revision'] and voice['source_fingerprint']==plan['candidate_fingerprint']
    assert voice['latency_options']==first['latency_options']
    for key in ('fact_revision_history','confirmed_transcript_deletion','conversation_source_dependencies'):assert voice['conversation_memory'][key]==1
    receipt['after_guard']=gate();assert listeners()==receipt['other_listeners']
    later=models();assert all(row in later for row in receipt['models_before']),'Existing model owner changed'
    receipt['checkpoint_after']=checkpoint('after')
    for kind,old in receipt['checkpoint_before']['databases'].items():
        if old['exists']:
            new=receipt['checkpoint_after']['databases'][kind]['counts']
            assert all(old['counts'][table]==new[table] for table in old['counts']),kind
    receipt.update(status='COMMITTED',revision=voice['service_revision'],fingerprint=voice['source_fingerprint'],
        latency_options=voice['latency_options'],health_memory=voice['conversation_memory'],
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:
    receipt.update(status='ABORTED_BEFORE_CHANGES' if not receipt.get('stop_voice') else 'ROLLING_BACK',error=type(exc).__name__+': '+str(exc));save()
    if receipt.get('stop_voice'):
        owners(True)
        for name in receipt['applied']:
            path=A/name;entry=plan['files'][name]
            assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['candidate'],'Concurrent source change during rollback: '+name
            if entry['before'] is None:path.unlink()
            else:shutil.copy2(H/'before'/name,path)
        receipt['rollback_revision']=start()['service_revision'];receipt['status']='ROLLED_BACK_CODE_LATEST_DATABASE_RETAINED';save()
    raise
save();print(json.dumps({'status':receipt['status'],'revision':receipt['revision'],'fingerprint':receipt['fingerprint'],'board_migration':False,'other_listeners_preserved':True}))

