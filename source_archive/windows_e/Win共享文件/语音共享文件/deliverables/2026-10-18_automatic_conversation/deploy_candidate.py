"""Activate automatic turn-taking with a reversible UI-only unit switch."""
import json
import hashlib
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

candidate=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
assert candidate['status']=='CANDIDATE_TESTED_NOT_ACTIVATED' and candidate['board_tests_passed']
for name,sha in candidate['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
remote=r'''
import hashlib,json,os,re,shutil,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])
assert root.parent==stage and stage.parent==Path('/home/root/aura-automatic-conversation-20261018')
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4) as r:return json.load(r)
def idle():
    s=get(8783,'/api/state')
    assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
    assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
    assert not s.get('automatic_conversation',{}).get('enabled')
    return s
before=idle();camera=get(8790,'/health');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
health=get(8792,'/health','192.168.50.1')
assert health['ready'] and not health['busy'] and health['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
assert health['tts']=='omnivoice' and health['num_step']==16
for name,sha in c['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
unit_path=Path('/etc/systemd/system/aura-avatar-ui.service');old_unit=unit_path.read_bytes()
old_link=os.readlink(str(unit_path)) if unit_path.is_symlink() else None
match=re.search(r'^ExecStart=.*?--config (\S+)\s*$',old_unit.decode(),re.M);assert match
old_config_path=Path(match.group(1));old_config=json.loads(old_config_path.read_text());old_root=Path(old_config['runtime'])
assert str(old_root)==c['source_runtime'],'Active runtime changed since staging'
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
(backup/'aura-avatar-ui.service').write_bytes(old_unit)
(backup/'config.json').write_bytes(old_config_path.read_bytes())
(backup/'rollback.json').write_text(json.dumps({'unit_link':old_link,'config':str(old_config_path),'runtime':str(old_root)},indent=2))
for source in old_root.glob('*_settings.json'):
    target=root/source.name;assert not target.is_symlink();target.write_bytes(source.read_bytes())
for name in ('managed-runs','stage.log','launch.json'):
    target=root/name
    if target.is_symlink():target.unlink()  # Only remove the isolated candidate's link.
(root/'managed-runs').mkdir(exist_ok=True)
startup=stage/'startup';startup.mkdir()
shutil.copy2(old_config_path.with_name('launcher.py'),startup/'launcher.py')
config=dict(old_config,runtime=str(root),gui_sha256=c['files']['aura/tools/board_avatar_gtk.py'])
config['component_sha256']=dict(old_config.get('component_sha256',{}))
for name,sha in c['files'].items():
    if name.startswith('aura/'):config['component_sha256'][name[5:]]=sha
(startup/'config.json').write_text(json.dumps(config,indent=2)+'\n')
env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin')
preflight=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=40)
(backup/'preflight.log').write_text(preflight.stdout+preflight.stderr)
if preflight.returncode:raise RuntimeError((preflight.stdout+preflight.stderr)[-3000:])
unit=old_unit.decode().replace(str(old_root),str(root))
unit=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+' --config '+str(startup/'config.json'),unit,flags=re.M)
(startup/'aura-avatar-ui.service').write_text(unit)
def atomic(raw):
    temporary=unit_path.with_name(unit_path.name+'.automatic-tmp');temporary.write_bytes(raw);temporary.chmod(0o644);os.replace(temporary,unit_path)
def service(*args):return subprocess.run(['systemctl',*args],check=True,capture_output=True,text=True,timeout=40)
report={'status':'STARTING','runtime':str(root),'stage':str(stage),'startup':str(startup),'backup':str(backup),
        'old_runtime':str(old_root),'camera_before':camera,'boot_before':boot,'voice_models_on_board':False,'pc_health':health}
try:
    idle();service('stop','aura-avatar-ui.service');atomic(unit.encode());service('daemon-reload');service('start','--no-block','aura-avatar-ui.service')
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        try:
            state=get(8783,'/api/state');auto=state.get('automatic_conversation',{})
            active=subprocess.run(['systemctl','is-active','aura-avatar-ui.service'],capture_output=True,text=True,timeout=5).stdout.strip()
            if state.get('error'):raise RuntimeError(state['error'])
            if active=='active' and state.get('audio_output_state')=='IDLE_READY' and auto.get('can_start') and not auto.get('enabled'):break
        except (OSError,ValueError):pass
        time.sleep(.3)
    else:raise RuntimeError('Automatic conversation UI did not become ready')
    report.update(status='DEPLOYED_READY_NOT_LISTENING',state=state)
except Exception as exc:
    subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=35)
    if old_link:
        temporary=unit_path.with_name(unit_path.name+'.automatic-rollback');temporary.symlink_to(old_link);os.replace(temporary,unit_path)
    else:atomic(old_unit)
    subprocess.run(['systemctl','daemon-reload'],capture_output=True,timeout=20)
    subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],capture_output=True,timeout=20)
    report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
after=get(8790,'/health')
report.update(camera_after=after,camera_preserved=after['pid']==camera['pid'],boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot)
(stage/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report))
'''.replace('CANDIDATE',repr(candidate))
report=json.loads(ssh('python3 -',remote,timeout=240))
(HERE/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('state','camera_before','camera_after','pc_health')},ensure_ascii=True))
assert report['status']=='DEPLOYED_READY_NOT_LISTENING' and report['camera_preserved'] and report['boot_preserved']
