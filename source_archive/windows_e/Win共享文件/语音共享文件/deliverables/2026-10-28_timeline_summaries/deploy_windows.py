"""Apply the frozen r2 host candidate; preserve the newer board and latest DBs."""
import datetime,hashlib,json,shutil,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';old=H.parent/'2026-10-28_device_skills'
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
plan=json.loads((H/'deployment_preview.json').read_text(encoding='utf-8'))
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
progress=json.loads((H/'PROGRESS.json').read_text(encoding='utf-8-sig'))
assert progress['user_hold_board'] is False and baseline['preflight_ready']
assert json.loads((H/'arm_tests.json').read_text(encoding='utf-8'))['returncode']==0
target=H/'deployment.json'
if target.exists():
    previous=json.loads(target.read_text(encoding='utf-8'))
    assert previous['status']=='ROLLED_BACK_CODE_LATEST_DATABASE_RETAINED' and not (H/'deployment_first_timeout.json').exists(),'Inspect the existing deployment receipt'
    shutil.copy2(target,H/'deployment_first_timeout.json')
receipt={'status':'PREPARING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'board_runtime':baseline['actual_runtime'],'board_boot':baseline['boot'],'board_source_changed':False,'board_ui_restarted':False,
    'other_models_stopped':False,'before_source':plan['expected_production_fingerprint']}
def save():target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def ps(args,timeout=40):
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*args],capture_output=True,timeout=timeout)
    if result.returncode:
        (H/'launcher_error.log').write_bytes(result.stdout+result.stderr)
        raise RuntimeError((result.stdout+result.stderr).decode('utf-8',errors='replace')[-1000:])
    return result.stdout.decode('utf-8-sig',errors='replace')
def health(port):
    with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:return json.load(response)
def owned(group,stop=False):
    return json.loads(ps(['-File',str(H/'manage_owned.ps1'),'-Group',group,'-AllowAbsent']+(['-Stop'] if stop else [])))
def gate():
    script=r'''
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
b=BASELINE
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==b['boot']
assert b['actual_config'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
path=Path(b['actual_config']);assert hashlib.sha256(path.read_bytes()).hexdigest()==b['config_sha256']
c=json.loads(path.read_text());assert c['runtime']==b['actual_runtime'] and c['component_sha256']==b['pins']
assert all(hashlib.sha256((Path(c['runtime'])/'aura'/n).read_bytes()).hexdigest()==h for n,h in b['pins'].items())
for _ in range(2):
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
 assert s['phase']=='IDLE' and s['playing'] is False and s['audio_output_state']=='IDLE_READY' and not s['error']
 assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
 p=s['manual_pan'];assert p['automatic_following'] is False
 assert p['state']==b['pan']['state'] and p['pulse_us']==b['pan']['pulse_us']
 assert not any(p.get(k) for k in ('busy','moving','active_motion','motion_active'))
 assert {k:s['ui_settings'].get(k) for k in b['settings']}==b['settings']
 time.sleep(.25)
pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
assert pid==b['camera_service']['MainPID']
print(json.dumps({'boot':b['boot'],'runtime':c['runtime'],'pins':len(b['pins']),'camera_pid':pid,'pan_state':p['state'],'pulse_us':p['pulse_us'],'idle_paused':True}))
'''.replace('BASELINE',repr(baseline))
    return json.loads(ssh('python3 -B -',script,timeout=20))
def checkpoint(phase):
    token=uuid.uuid4().hex;ps(['-File',str(H/'start_checkpoint.ps1'),'-Job',token,'-Phase',phase])
    path=H/('db_checkpoint_'+token+'.json');until=time.monotonic()+25
    while time.monotonic()<until:
        if path.exists():
            value=json.loads(path.read_text(encoding='utf-8'))
            assert value['status']=='PASS',value.get('error');return value
        time.sleep(.2)
    raise TimeoutError('Production-view database checkpoint timed out')
def start_hub():
    ps(['-File',str(old/'start_devices.ps1')]);until=time.monotonic()+65
    while time.monotonic()<until:
        try:
            value=health(8812)
            if value.get('speaker_ready'):return value
        except (OSError,ValueError):pass
        time.sleep(.3)
    raise TimeoutError('CPU device service did not become ready')
def start_voice(diagnostics=True):
    launcher=H/'start_voice_diagnostic.ps1' if diagnostics else H.parent/'2026-10-18_board_dialogue/start_background_models.ps1'
    value=ps(['-File',str(launcher)],timeout=460)
    (H/'voice_restart.log').write_text(value,encoding='utf-8');return health(8792)

receipt['guard']=gate()
for name,entry in plan['files'].items():
    source=A/name;candidate=H/'candidate_source'/name
    assert (hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None)==entry['before'],'Concurrent source change: '+name
    assert hashlib.sha256(candidate.read_bytes()).hexdigest()==entry['candidate']
starter=Path(plan['device_startup']['path'])
assert hashlib.sha256(starter.read_bytes()).hexdigest()==plan['device_startup']['before']
receipt['owners']={k:owned(k) for k in ('voice','hub')}
receipt['models_before']=json.loads(ps(['-Command',"@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'ollama*' -or $_.Name -eq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,Name) | ConvertTo-Json -Compress"]))
receipt['timezone_preflight']=subprocess.check_output([r'D:\AIModels\speaker-identity\venv\Scripts\python.exe','-B','-c',
    "from zoneinfo import ZoneInfo;print(ZoneInfo('America/Los_Angeles'))"],text=True).strip()
receipt['files']=plan['files'];save()
try:
    gate();receipt['stop_voice']=owned('voice',True);receipt['stop_hub']=owned('hub',True);save()
    receipt['checkpoint_before']=checkpoint('before');save()
    for name in plan['files']:
        path=A/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(H/'candidate_source'/name,path)
    shutil.copy2(H/'start_devices_candidate.py',starter);receipt['status']='STARTING';save()
    hub=start_hub();assert hub['revision']==plan['hub_candidate'] and hub['timeline']['background_summaries']['running']
    voice=start_voice();assert voice['ready'] and voice['service_revision']==plan['candidate_revision']
    assert voice['source_fingerprint']==plan['candidate_fingerprint'] and voice['conversation_memory']['background_summaries']['running']
    receipt['after_guard']=gate();receipt['checkpoint_after']=checkpoint('after')
    for kind,data in receipt['checkpoint_before']['databases'].items():
        if data['exists']:
            later=receipt['checkpoint_after']['databases'][kind]['counts']
            assert all(later[t]==n for t,n in data['counts'].items()),'Authoritative table counts changed: '+kind
    receipt.update(status='COMMITTED',after_voice={'revision':voice['service_revision'],'fingerprint':voice['source_fingerprint'],
        'summary_worker':voice['conversation_memory']['background_summaries']},after_hub=hub,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:
    receipt['error']=type(exc).__name__+': '+str(exc);receipt['status']='ROLLING_BACK';save()
    if 'stop_voice' not in receipt:receipt['status']='ABORTED_WITHOUT_SOURCE_CHANGES';save();raise
    owned('voice',True);owned('hub',True)
    for name,entry in plan['files'].items():
        path=A/name;prior=H/'before'/name
        if prior.exists():shutil.copy2(prior,path)
        elif path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==entry['candidate']:path.unlink()
    shutil.copy2(H/'start_devices_before.py',starter)
    receipt['rollback_hub']=start_hub()['revision'];receipt['rollback_voice']=start_voice(diagnostics=False)['service_revision']
    receipt['status']='ROLLED_BACK_CODE_LATEST_DATABASE_RETAINED';save();raise
save();print(json.dumps({'status':receipt['status'],'voice':receipt['after_voice'],'hub':hub['revision'],
    'board_runtime':baseline['actual_runtime'],'pan_preserved':receipt['after_guard']['pulse_us'],'production_view_snapshots':True}))
