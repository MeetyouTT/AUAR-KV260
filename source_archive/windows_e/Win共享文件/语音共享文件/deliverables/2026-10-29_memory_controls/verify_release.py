"""Read-only final verification and independent production-view snapshots."""
import ast,datetime,hashlib,json,socket,subprocess,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint,require_current_voice
from common import frontend_wire,portrait_wire
from board_ssh import ssh
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
receipt=json.loads((H/'deployment.json').read_text(encoding='utf-8'))
assert receipt['status']=='COMMITTED'
report={'status':'STARTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def health(port):
    with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:return json.load(response)
try:
    for name,entry in plan['files'].items():assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['candidate'],name
    assert hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()==plan['preserved_latency_sha256']
    services={str(p):health(p) for p in (8791,8792,8812)}
    for port,wire in ((8795,frontend_wire),(8796,portrait_wire)):
        with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
            wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});value,payload=wire.receive(connection,0 if port==8796 else 3)
            assert value['ready'] and not payload;services[str(port)]=value
    voice=services['8792']
    require_current_voice(voice,json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model'],source_fingerprint(A))
    assert voice['ready'] and not voice['busy'] and voice['service_revision']==plan['candidate_revision']
    assert voice['source_fingerprint']==plan['candidate_fingerprint'] and voice['latency_options']['compact_grammar'] is False
    assert voice['conversation_memory']['background_summaries']['running'] and not voice['conversation_memory']['background_summaries']['error']
    # Import definitions only; no top-level deployment code or mutations execute.
    tree=ast.parse((H/'deploy_windows.py').read_text(encoding='utf-8'))
    definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('ps','gate','models','listeners')]
    env=dict(globals());exec(compile(ast.Module(body=definitions,type_ignores=[]),'readonly_gate','exec'),env)
    board=env['gate']();assert env['listeners']()==receipt['other_listeners']
    current=env['models']();assert all(r in current for r in receipt['models_before'])
    assert not (H/'physical_database_check.json').exists(),'Inspect existing final private check'
    python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    command='"'+python+'" -B "'+str(H/'verify_private.py')+'"'
    launch="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$s};if($p.ReturnValue -ne 0){throw 'Private verification launch failed'}"
    subprocess.run(['powershell.exe','-NoProfile','-Command',launch],check=True,capture_output=True,timeout=15)
    until=time.monotonic()+25
    while time.monotonic()<until and not (H/'physical_database_check.json').exists():time.sleep(.2)
    private=json.loads((H/'physical_database_check.json').read_text(encoding='utf-8'));assert private['status']=='PASS',private.get('error')
    memory=json.loads((H/'live_controls_acceptance.json').read_text(encoding='utf-8'))
    regular=json.loads((H/'live_voice_acceptance.json').read_text(encoding='utf-8'))
    assert memory['status']==regular['status']=='PASS' and memory['cleanup']['only_public_test_conversation_removed']
    report.update(status='PASS',revision=voice['service_revision'],fingerprint=voice['source_fingerprint'],source_files_verified=len(plan['files']),
        latency_options=voice['latency_options'],memory_health=voice['conversation_memory'],board=board,
        other_models_preserved=True,other_listeners_preserved=True,original_database_sources_unchanged=True,
        public_test_rows_removed=True,board_migration=False,board_ui_restarted=False,camera_restarted=False,
        services={p:{k:v[k] for k in ('ready','busy','revision','speaker_ready') if k in v} for p,v in services.items()},
        live_memory_checks=len(memory['turns']),live_voice_checks=len(regular['checks']))
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'release_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True));raise SystemExit(0 if report['status']=='PASS' else 1)

