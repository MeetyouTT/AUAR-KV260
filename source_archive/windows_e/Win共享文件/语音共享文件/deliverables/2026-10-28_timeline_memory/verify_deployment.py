"""Readonly source, additive-schema, dependency, and actual board-state checks."""
import datetime,hashlib,json,socket,sqlite3,subprocess,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.voice_service_capabilities import require_current_voice,source_fingerprint
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
deployment=json.loads((H/'deployment.json').read_text(encoding='utf-8'));assert deployment['status']=='COMMITTED'
baseline=json.loads((H/'runtime_current.json').read_text(encoding='utf-8'))
assert baseline['ready_for_readonly_completion'] and baseline['component_pins_unchanged'] and not baseline['hash_mismatches']
def health(port):
    with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:return json.load(response)
checks={str(p):health(p) for p in (8791,8792,8812)}
from common import frontend_wire,portrait_wire
for port,wire in ((8795,frontend_wire),(8796,portrait_wire)):
    with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
        wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'})
        value,data=wire.receive(connection,0 if port==8796 else 3)
        assert not data and value.get('ready') is True
        checks[str(port)]=value
voice=checks['8792'];require_current_voice(voice,json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model'],source_fingerprint(A))
assert voice['conversation_memory']['timeline_version']==1
assert checks['8812']['timeline']['version']==1 and checks['8812']['speaker_ready']
assert all(hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['after'] for name,entry in deployment['files'].items())
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','read_only':True,
        'deployment_boot':deployment['guard']['boot'],'rebooted_since_deployment':baseline['boot']!=deployment['guard']['boot'],
        'windows_source_fingerprint':voice['source_fingerprint'],'windows_revision':voice['service_revision'],
        'services':{p:{k:v[k] for k in ('ready','busy','revision','speaker_ready','speaker_calibrated','timeline') if k in v} for p,v in checks.items()},
        'source_files_verified':len(deployment['files']),'database_checks':{}}
for name,source in [('conversation',H.parent/'2026-10-18_board_dialogue/model_host/conversations.sqlite3')]:
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        counts={r[0]:db.execute('SELECT count(*) FROM "'+r[0]+'"').fetchone()[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    before=deployment['database_backups'][name]['counts']
    assert all(counts[t]==n for t,n in before.items()),'Pre-existing archive counts changed'
    report['database_checks'][name]={'integrity':'ok','preexisting_counts_preserved':True,'counts':counts}
physical=json.loads((H/'physical_database_check.json').read_text(encoding='utf-8'))
assert physical['status']=='PASS' and physical['databases']['observation']['integrity']=='ok'
assert 'visual_timeline' in physical['databases']['observation']['tables']
report['database_checks']['observation']={'integrity':'ok','counts':physical['databases']['observation']['counts'],
    'source':'independent_WMI_production_file_view','as_of':physical['checked_utc'],
    'private_snapshot_kind':'post_upgrade',
    'pre_upgrade_agent_snapshot_is_not_production_view':True}
script=r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
v=BEFORE
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==v['boot']
entry=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert v['actual_config'] in entry
cfg=json.loads(Path(v['actual_config']).read_text());root=Path(cfg['runtime'])/'aura'
assert len(cfg['component_sha256'])==277 and all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in cfg['component_sha256'].items())
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s['playing'] and not s['error']
assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
assert s['manual_pan']['automatic_following'] is False and s['manual_pan']['state']=='FAULT' and s['manual_pan']['pulse_us'] is None
pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
assert pid==v['camera_service']['MainPID']
health={}
for port in (8792,8812):
 with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:h=json.load(response)
 health[str(port)]={k:h[k] for k in ('ready','service_revision','speaker_ready','timeline') if k in h}
print(json.dumps({'boot':v['boot'],'runtime':cfg['runtime'],'component_pins_verified':277,'camera_pid':pid,
 'phase':s['phase'],'listening':s['handsfree_dialogue']['enabled'],'microphone_open':s['handsfree_dialogue']['microphone_open'],
 'following':s['manual_pan']['automatic_following'],'mechanical':s['manual_pan']['state'],
 'mixer':{k:s['ui_settings'].get(k) for k in ('volume','muted')},'display':s['avatar_display'],'windows_from_board':health}))
'''.replace('BEFORE',repr(baseline))
report['board']=json.loads(ssh('python3 -B -',script,timeout=25))
assert report['board']['windows_from_board']['8792']['service_revision']==voice['service_revision']
command="@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'ollama*' -or $_.Name -eq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,Name) | ConvertTo-Json -Compress"
current=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True))
old=deployment['models_before'];old=old if isinstance(old,list) else [old];current=current if isinstance(current,list) else [current]
assert all(row in current for row in old),'A pre-existing model owner changed'
report['other_model_owners_preserved']=True;report['other_model_pids']=[r['ProcessId'] for r in old]
(H/'release_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
