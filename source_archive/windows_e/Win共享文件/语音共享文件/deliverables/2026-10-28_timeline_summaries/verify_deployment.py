"""Fresh read-only checks against this deployment's actual board baseline."""
import ast,datetime,hashlib,json,socket,subprocess,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.voice_service_capabilities import require_current_voice,source_fingerprint
from common import frontend_wire,portrait_wire
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
report={'status':'STARTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def health(port):
    with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:return json.load(response)
try:
    deployment=json.loads((H/'deployment.json').read_text(encoding='utf-8'));assert deployment['status']=='COMMITTED'
    baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
    plan=json.loads((H/'deployment_preview.json').read_text(encoding='utf-8'))
    for name,entry in plan['files'].items():assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['candidate'],name
    starter=plan['device_startup'];assert hashlib.sha256(Path(starter['path']).read_bytes()).hexdigest()==starter['candidate']
    services={str(p):health(p) for p in (8791,8792,8812)}
    for port,wire in ((8795,frontend_wire),(8796,portrait_wire)):
        with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
            wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'})
            value,data=wire.receive(connection,0 if port==8796 else 3)
            assert not data and value.get('ready') is True
            services[str(port)]=value
    voice=services['8792'];require_current_voice(voice,json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model'],source_fingerprint(A))
    assert voice['ready'] and not voice['busy'] and voice['service_revision']==plan['candidate_revision']
    assert voice['source_fingerprint']==plan['candidate_fingerprint']
    hub=services['8812'];assert hub['revision']==plan['hub_candidate'] and hub['speaker_ready']
    for worker in (voice['conversation_memory']['background_summaries'],hub['timeline']['background_summaries']):
        assert worker['running'] and not worker['error'] and worker['model_inference'] is False
    # Reuse only the read-only remote script constant; do not overwrite baseline.
    tree=ast.parse((H/'capture_board.py').read_text(encoding='utf-8'))
    script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
    board=json.loads(ssh('python3 -B -',script,timeout=20))
    assert board['preflight_ready'] and not board['hash_mismatches']
    for key in ('boot','actual_runtime','actual_config','config_sha256','pins','settings','pan'):assert board[key]==baseline[key],'Board state changed: '+key
    for service in ('ui_service','camera_service'):
        for key in ('MainPID','NRestarts','ExecStart','ActiveState','SubState'):assert board[service][key]==baseline[service][key],service+':'+key
    command="@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'ollama*' -or $_.Name -eq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,Name) | ConvertTo-Json -Compress"
    current=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True))
    current=current if isinstance(current,list) else [current]
    assert all(row in current for row in deployment['models_before']),'A pre-existing model owner changed'
    helper=H/'verify_private.py';python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    assert not (H/'physical_database_check.json').exists(),'Inspect the existing final private check before repeating'
    command='"'+python+'" -B "'+str(helper)+'"'
    launch="$setup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$setup};if($p.ReturnValue -ne 0){throw 'Private check launch failed'}"
    subprocess.run(['powershell.exe','-NoProfile','-Command',launch],check=True,capture_output=True,timeout=15)
    until=time.monotonic()+25
    while time.monotonic()<until and not (H/'physical_database_check.json').exists():time.sleep(.2)
    private=json.loads((H/'physical_database_check.json').read_text(encoding='utf-8'));assert private['status']=='PASS',private.get('error')
    summary=json.loads((H/'live_summary_acceptance.json').read_text(encoding='utf-8'))
    regular=json.loads((H/'live_voice_acceptance.json').read_text(encoding='utf-8'))
    assert summary['status']==regular['status']=='PASS' and summary['voice']['history_messages']>0
    assert summary['voice']['current_picture_requested'] is False and summary['cleanup']['removed_only_probe']
    report.update(status='PASS',windows_revision=voice['service_revision'],source_fingerprint=voice['source_fingerprint'],source_files_verified=len(plan['files']),
        services={p:{k:v[k] for k in ('ready','busy','revision','speaker_ready') if k in v} for p,v in services.items()},
        summary_workers={'conversation':voice['conversation_memory']['background_summaries'],'visual':hub['timeline']['background_summaries']},
        board={'boot':board['boot'],'runtime':board['actual_runtime'],'component_pins_verified':len(board['pins']),
               'camera_pid':board['camera_service']['MainPID'],'ui_pid':board['ui_service']['MainPID'],'phase':board['phase'],
               'listening':board['listening'],'microphone_open':board['microphone_open'],'pan':board['pan'],'settings':board['settings'],
               'ui_not_restarted':True,'original_config_and_sources_preserved':True},
        other_model_owners_preserved=True,other_model_pids=[r['ProcessId'] for r in deployment['models_before']],
        original_database_sources_preserved=True,private_snapshot_evidence='physical_database_check.json',
        live_summary_checks=len(summary['checks']),live_voice_checks=len(regular['checks']))
except Exception as exc:
    report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'release_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True));raise SystemExit(0 if report['status']=='PASS' else 1)
