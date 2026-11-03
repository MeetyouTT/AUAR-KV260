"""Activate the tested voice UI with a new launcher release and reversible unit switch."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

candidate=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
cancel=json.loads((HERE/'cancellation.json').read_text(encoding='utf-8'))
integration=json.loads((HERE/'integration_first.json').read_text(encoding='utf-8'))
listening=json.loads((HERE/'listening_acceptance.json').read_text(encoding='utf-8'))
assert cancel['status']=='PASS_REAL_FEEDBACK_AND_ANSWER_CANCEL'
assert integration['status'].startswith('PASS_REAL_PLAYBACK_')
assert listening['user_report']=='完整清楚'
for name,sha in candidate['files'].items():
    if name.endswith('.py'):assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
remote=r'''
import hashlib,json,os,re,shutil,subprocess,time,urllib.request,uuid
from pathlib import Path
candidate=CANDIDATE
stage=Path(candidate['stage']);root=Path(candidate['runtime'])
assert root.parent==stage and stage.parent==Path('/home/root/aura-stream-playback-20261018')
for name,sha in candidate['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,'Candidate source changed: '+name
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=3) as response:return json.load(response)
def idle():
    state=get(8783,'/api/state')
    if 'phase' not in state:raise OSError('UI is initializing its first state')
    assert state['phase']=='IDLE' and not state['playing'] and not state['paused'],'Board playback busy'
    assert state['local_recording']['state']!='RECORDING' and not state['local_transcription']['service']['pending'],'Board recording busy'
    return state
deadline=time.monotonic()+120
while True:
    try:idle();break
    except (OSError,ValueError):
        if time.monotonic()>=deadline:raise RuntimeError('Previous UI did not recover before activation')
        time.sleep(.5)
camera=get(8790,'/health');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
health=get(8792,'/health','192.168.50.1')
assert health['ready'] and health['thinking_feedback_ready'] and not health['busy'],'PC voice service not idle/ready'
assert health['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and health['num_step']==16
unit_path=Path('/etc/systemd/system/aura-avatar-ui.service')
old_unit=unit_path.read_bytes();old_link=os.readlink(str(unit_path)) if unit_path.is_symlink() else None
match=re.search(r'^ExecStart=.*?--config (\S+)\s*$',old_unit.decode(),re.M)
if not match:raise RuntimeError('Unrecognized current voice UI launcher')
old_config_path=Path(match.group(1));old_config=json.loads(old_config_path.read_text())
old_root=Path(old_config['runtime'])
backup=stage/('activation-backup-'+uuid.uuid4().hex[:12]);backup.mkdir()
(backup/'aura-avatar-ui.service').write_bytes(old_unit)
(backup/'config.json').write_bytes(old_config_path.read_bytes())
(backup/'rollback.json').write_text(json.dumps({'unit_link':old_link,'config':str(old_config_path),'runtime':str(old_root)},indent=2))
for source in old_root.glob('*_settings.json'):
    target=root/source.name
    if target.is_symlink():raise RuntimeError('Mutable settings unexpectedly linked')
    target.write_bytes(source.read_bytes())
for name in ('managed-runs','stage.log','launch.json'):
    target=root/name
    if target.is_symlink():target.unlink()  # Candidate link only; preserve every original target.
(root/'managed-runs').mkdir(exist_ok=True)
startup=stage/'startup';startup.mkdir(exist_ok=True)
shutil.copy2(str(old_config_path.with_name('launcher.py')),str(startup/'launcher.py'))
config=dict(old_config,runtime=str(root),gui_sha256=candidate['files']['aura/tools/board_avatar_gtk.py'])
config['component_sha256']=dict(old_config.get('component_sha256',{}))
for name,sha in candidate['files'].items():
    if name.startswith('aura/'):config['component_sha256'][name[5:]]=sha
(startup/'config.json').write_text(json.dumps(config,indent=2)+'\n')
environment=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin')
preflight=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
                         env=environment,capture_output=True,text=True,timeout=30)
(backup/'preflight.log').write_text(preflight.stdout+preflight.stderr)
if preflight.returncode:raise RuntimeError(preflight.stdout+preflight.stderr)
unit=old_unit.decode().replace(str(old_root),str(root))
unit=re.sub(r'^ExecStart=.*$', 'ExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+' --config '+str(startup/'config.json'),unit,flags=re.M)
(startup/'aura-avatar-ui.service').write_text(unit)
def atomic_unit(raw):
    temporary=unit_path.with_name(unit_path.name+'.aura-stream-tmp')
    temporary.write_bytes(raw);temporary.chmod(0o644);os.replace(str(temporary),str(unit_path))
def service(*args):return subprocess.run(['systemctl',*args],check=True,capture_output=True,text=True,timeout=40)
report={'status':'STARTING','runtime':str(root),'startup':str(startup),'backup':str(backup),
        'old_runtime':str(old_root),'old_config':str(old_config_path),'camera_pid_before':camera['pid'],
        'voice_models_on_board':False,'llm_model':health['llm_model'],'source_files':candidate['files']}
try:
    idle();service('stop','aura-avatar-ui.service')
    atomic_unit(unit.encode());service('daemon-reload');service('start','--no-block','aura-avatar-ui.service')
    deadline=time.monotonic()+140;last_error=''
    while time.monotonic()<deadline:
        try:
            state=get(8783,'/api/state')
            if state.get('error'):raise RuntimeError(state['error'])
            voice=state.get('local_transcription',{}).get('service',{})
            unit_state=subprocess.run(['systemctl','is-active','aura-avatar-ui.service'],capture_output=True,text=True,timeout=5).stdout.strip()
            if (voice.get('streaming') and voice.get('feedback_ready') and
                    state.get('audio_output_state')=='IDLE_READY' and unit_state=='active'):break
        except Exception as exc:last_error=str(exc)
        time.sleep(.5)
    else:raise RuntimeError('New voice UI not ready: '+last_error)
    report.update(status='DEPLOYED_READY',state=state,
        service_state=service('is-active','aura-avatar-ui.service').stdout.strip())
except Exception as exc:
    subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=35)
    if old_link:
        temporary=unit_path.with_name(unit_path.name+'.aura-stream-rollback')
        temporary.symlink_to(old_link);os.replace(str(temporary),str(unit_path))
    else:atomic_unit(old_unit)
    subprocess.run(['systemctl','daemon-reload'],capture_output=True,timeout=20)
    subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],capture_output=True,timeout=20)
    report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
after=get(8790,'/health')
report.update(camera_pid_after=after['pid'],camera_preserved=camera['pid']==after['pid'],
              board_boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot)
(stage/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report))
'''.replace('CANDIDATE',repr(candidate))
report=json.loads(ssh('python3 -',remote,timeout=360))
(HERE/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key not in ('state','source_files')},ensure_ascii=False))
if report['status']!='DEPLOYED_READY' or not report['camera_preserved'] or not report['board_boot_preserved']:raise SystemExit(1)
