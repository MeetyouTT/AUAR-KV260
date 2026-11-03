"""Idle-only host update. Source rollback preserves the newest authoritative DB."""
import datetime,hashlib,json,shutil,sqlite3,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
before=json.loads((H/'runtime_before.json').read_text(encoding='utf-8'))
old=H.parent/'2026-10-28_device_skills';starter=old/'start_devices.py'
RECEIPT=H/'deployment.json'
if RECEIPT.exists():
    previous=json.loads(RECEIPT.read_text(encoding='utf-8'))
    if previous['status']=='ROLLED_BACK_CODE_DATABASE_RETAINED' and not (H/'deployment_first_rollback.json').exists():
        shutil.copy2(RECEIPT,H/'deployment_first_rollback.json')
    else:raise RuntimeError('Deployment receipt exists; inspect it before another change')
receipt={'status':'PREPARING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'board_ui_restarted':False,'board_source_changed':False,'other_models_stopped':False}
def save():RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def health(port):
    with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:return json.load(response)
def ps(args,*,timeout=40):
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*args],capture_output=True,timeout=timeout)
    if result.returncode:raise RuntimeError((result.stderr+result.stdout).decode('utf-8',errors='replace')[-1200:])
    return result.stdout.decode('utf-8-sig')
def owned(group,stop=False):
    return json.loads(ps(['-File',str(H/'manage_owned.ps1'),'-Group',group]+(['-Stop','-AllowAbsent'] if stop else [])))
def gate():
    script=r'''
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
v=BEFORE
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==v['boot'],'Board rebooted; revalidate'
assert v['actual_config'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
cfg=json.loads(Path(v['actual_config']).read_text());root=Path(cfg['runtime'])/'aura'
assert cfg['runtime']==v['actual_runtime']
assert len(cfg['component_sha256'])==277
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in cfg['component_sha256'].items())
for _ in range(2):
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as response:s=json.load(response)
 assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='IDLE_READY' and not s['error']
 assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
 assert s['manual_pan']['automatic_following'] is False and s['manual_pan']['pulse_us'] is None and s['manual_pan']['state']=='FAULT'
 assert not s['ui_settings'].get('pending')
 time.sleep(.3)
print(json.dumps({'boot':v['boot'],'pins':277,'idle_paused':True,'camera_pid':subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()}))
'''.replace('BEFORE',repr(before))
    return json.loads(ssh('python3 -B -',script,timeout=20))
def backup_database(source,name):
    source=Path(source)
    if not source.is_file():return {'exists':False}
    private=Path.home()/'AppData/Local/Aura/memory-upgrades'/('timeline-20261028-'+receipt['backup_run'])
    private.mkdir(parents=True,exist_ok=True);target=private/name
    with sqlite3.connect(str(source)) as original,sqlite3.connect(str(target)) as backup:
        original.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        counts={r[0]:backup.execute('SELECT count(*) FROM "'+r[0]+'"').fetchone()[0] for r in backup.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    return {'exists':True,'private_snapshot':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'counts':counts}
def launch_voice():
    output=ps(['-File',str(H.parent/'2026-10-18_board_dialogue/start_background_models.ps1')],timeout=460)
    (H/'voice_restart.log').write_text(output,encoding='utf-8')
    return health(8792)
def launch_hub():
    ps(['-File',str(old/'start_devices.ps1')])
    deadline=time.monotonic()+65
    while time.monotonic()<deadline:
        try:
            value=health(8812)
            if value.get('speaker_ready'):return value
        except (OSError,ValueError):pass
        time.sleep(.3)
    raise TimeoutError('Device service readiness timeout')

receipt['guard']=gate();voice=health(8792);hub=health(8812)
assert voice['ready'] and not voice['busy'] and voice['service_revision']=='voice-device-skills-20261028-r6'
assert hub['revision']=='device-skills-v1' and hub['speaker_ready']
receipt['before_voice']={'revision':voice['service_revision'],'fingerprint':voice['source_fingerprint']}
receipt['before_hub']={'revision':hub['revision'],'pid':hub['pid']}
receipt['owners']={'voice':owned('voice'),'hub':owned('hub')}
receipt['timezone_preflight']=subprocess.check_output([r'D:\AIModels\speaker-identity\venv\Scripts\python.exe','-B','-c',
    "from zoneinfo import ZoneInfo;print(ZoneInfo('America/Los_Angeles'))"],text=True).strip()
receipt['models_before']=json.loads(ps(['-Command',"@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'ollama*' -or $_.Name -eq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,Name) | ConvertTo-Json -Compress"]))
names=[];receipt['files']={}
for path in sorted((H/'candidate_source').rglob('*')):
    if not path.is_file() or path.suffix not in ('.py','.json'):continue
    name=path.relative_to(H/'candidate_source').as_posix();target=A/name
    if target.exists() and target.read_bytes()==path.read_bytes():continue
    prior=H/'before'/name
    if target.exists():
        if prior.exists():assert prior.read_bytes()==target.read_bytes(),'Source changed: '+name
        else:raise RuntimeError('Existing source was not snapshotted: '+name)
    elif prior.exists():raise RuntimeError('Prior source unexpectedly missing: '+name)
    names.append(name);receipt['files'][name]={'before':hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
                                             'after':hashlib.sha256(path.read_bytes()).hexdigest()}
assert starter.read_bytes()==(H/'start_devices_before.py').read_bytes(),'Device startup changed'
receipt['backup_run']=uuid.uuid4().hex;save()
try:
    gate();assert not health(8792)['busy']
    receipt['stop_voice']=owned('voice',True);save()
    receipt['stop_hub']=owned('hub',True);save()
    receipt['database_backups']={
        'conversation':backup_database(H.parent/'2026-10-18_board_dialogue/model_host/conversations.sqlite3','conversations.sqlite3'),
        'observation':backup_database(Path.home()/'AppData/Local/Aura/device-memory/observations.sqlite3','observations.sqlite3')}
    for name in names:
        target=A/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(H/'candidate_source'/name,target)
    shutil.copy2(H/'start_devices_candidate.py',starter)
    receipt['status']='STARTING';save()
    new_hub=launch_hub();assert new_hub['revision']=='device-timeline-v1' and new_hub['timeline']['version']==1
    new_voice=launch_voice();assert new_voice['ready'] and new_voice['service_revision']=='voice-timeline-20261028-r1'
    assert new_voice['conversation_memory']['timeline_version']==1
    receipt['after_guard']=gate()
    assert receipt['after_guard']['camera_pid']==receipt['guard']['camera_pid'],'Camera owner changed during host deployment'
    receipt.update(status='COMMITTED',after_voice={'revision':new_voice['service_revision'],'fingerprint':new_voice['source_fingerprint']},
                   after_hub=new_hub,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:
    receipt['error']=type(exc).__name__+': '+str(exc)
    if 'stop_voice' not in receipt:
        receipt['status']='ABORTED_WITHOUT_CHANGES';save();raise
    owned('voice',True);owned('hub',True)
    for name in names:
        target=A/name;prior=H/'before'/name
        if prior.exists():shutil.copy2(prior,target)
        elif target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==receipt['files'][name]['after']:
            target.unlink() # Only our newly introduced exact file; never a recursive deletion.
    shutil.copy2(H/'start_devices_before.py',starter)
    receipt['rollback_hub']=launch_hub()['revision'];receipt['rollback_voice']=launch_voice()['service_revision']
    receipt['status']='ROLLED_BACK_CODE_DATABASE_RETAINED';save();raise
save();print(json.dumps({'status':receipt['status'],'voice':receipt['after_voice'],'hub':new_hub['revision'],
                        'changed_files':len(names),'board_ui_restarted':False,'private_backups':True}))
