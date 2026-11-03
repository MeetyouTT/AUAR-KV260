"""Verified incremental GTK voice deployment; no camera restart or platform changes."""
import base64
import hashlib
import json
from pathlib import Path
from board_ssh import ssh,HERE

ROOT=HERE.parents[1]
before=json.loads((HERE/'board_sources_before.json').read_text(encoding='utf-8'))
names=[name for name in before['files'] if name.startswith('aura/')]
files={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
identity=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]+'-r2'
payload={'id':identity,'runtime':before['runtime'],'files':files,'before':before['files'],
         'old_config':before['launcher_config'],'old_config_path':before['launcher_config_path']}
(HERE/'deployment_payload.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
remote=r'''
import base64,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
P=json.loads(base64.b64decode(PAYLOAD))
runtime=Path(P['runtime']).resolve()
assert str(runtime)=='/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009'
release=Path('/home/root/aura-voice-dialogue-20261018')/P['id']
if release.exists():raise RuntimeError('Release exists; inspect before rerunning')
cfg_path=Path(P['old_config_path'])
if json.loads(cfg_path.read_text())!=P['old_config']:raise RuntimeError('Launcher config changed since inventory')
raw_files={}
for name,encoded in P['files'].items():
    target=(runtime/name).resolve()
    if not str(target).startswith(str(runtime)+'/'):raise ValueError('Invalid target')
    raw=base64.b64decode(encoded)
    if target.suffix=='.py':compile(raw,str(target),'exec')
    old=P['before'][name]
    current=target.read_bytes() if target.exists() else None
    if (current is None)!=(old is None) or current is not None and hashlib.sha256(current).hexdigest()!=old['sha256']:
        raise RuntimeError('Board source changed: '+name)
    raw_files[name]=raw
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
wait_until=time.monotonic()+120
while True:
    try:
        with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as response:state=json.load(response)
        break
    except Exception:
        if time.monotonic()>=wait_until:raise
        time.sleep(2)
if state['phase']!='IDLE' or state['local_recording']['state']=='RECORDING':raise RuntimeError('UI is busy; deployment deferred')
with opener.open('http://192.168.50.1:8792/health',timeout=4) as response:health=json.load(response)
if not health.get('ready') or health.get('num_step')!=16:raise RuntimeError('Actual model host is not ready')
camera_pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],universal_newlines=True).strip()
release.mkdir(parents=True)
backup=release/'before';backup.mkdir()
for name in P['files']:
    target=runtime/name
    if target.exists():
        saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(target.read_bytes())
conversation=runtime/'avatar_conversation_settings.json'
if conversation.exists():(backup/'avatar_conversation_settings.json').write_bytes(conversation.read_bytes())
unit=Path('/etc/systemd/system/aura-avatar-ui.service')
old_unit=unit.read_bytes();(backup/'aura-avatar-ui.service').write_bytes(old_unit)
new_launcher=Path('/home/root/aura-ui-startup-20261009/releases')/('voice-'+P['id'])
new_launcher.mkdir()
old_launcher=cfg_path.with_name('launcher.py')
(new_launcher/'launcher.py').write_bytes(old_launcher.read_bytes())
config=dict(P['old_config']);config['component_sha256']=dict(config.get('component_sha256',{}))
for name,raw in raw_files.items():
    rel=name[len('aura/'):]
    if rel=='tools/board_avatar_gtk.py':config['gui_sha256']=hashlib.sha256(raw).hexdigest()
    else:config['component_sha256'][rel]=hashlib.sha256(raw).hexdigest()
(new_launcher/'config.json').write_text(json.dumps(config,indent=2)+'\n')
new_unit=old_unit.decode().replace(str(cfg_path.parent),str(new_launcher))
if new_unit==old_unit.decode():raise RuntimeError('Unit did not reference inventoried launcher')
def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.voice-tmp');temp.write_bytes(raw);os.replace(str(temp),str(path))
result={'release_id':P['id'],'runtime':str(runtime),'backup':str(backup),'new_launcher':str(new_launcher),
        'camera_pid_before':camera_pid,'files':{},'source_scope':'GTK client and voice transport only'}
try:
    subprocess.check_call(['systemctl','stop','aura-avatar-ui.service'])
    for name,raw in raw_files.items():
        target=runtime/name;atomic(target,raw)
        sha=hashlib.sha256(target.read_bytes()).hexdigest()
        assert sha==hashlib.sha256(raw).hexdigest()
        result['files'][name]={'sha256':sha,'bytes':len(raw)}
    settings={'enabled':True,'host':'192.168.50.1','port':8792,'timeout_ms':120000}
    atomic(conversation,(json.dumps(settings,indent=2)+'\n').encode())
    atomic(unit,new_unit.encode());subprocess.check_call(['systemctl','daemon-reload'])
    preflight=subprocess.run(['python3',str(new_launcher/'launcher.py'),'--config',str(new_launcher/'config.json'),'--preflight'],
                             env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
    (release/'preflight.log').write_text(preflight.stdout)
    if preflight.returncode:raise RuntimeError('Startup preflight failed: '+preflight.stdout[-1000:])
    subprocess.check_call(['systemctl','start','--no-block','aura-avatar-ui.service'])
    result['status']='DEPLOYED_STARTING'
except Exception as exc:
    subprocess.call(['systemctl','stop','aura-avatar-ui.service'])
    for name,raw in raw_files.items():
        target=runtime/name;saved=backup/name
        if saved.exists():atomic(target,saved.read_bytes())
        elif target.exists():target.unlink()
    old_conversation=backup/'avatar_conversation_settings.json'
    if old_conversation.exists():atomic(conversation,old_conversation.read_bytes())
    elif conversation.exists():conversation.unlink()
    atomic(unit,old_unit);subprocess.call(['systemctl','daemon-reload'])
    subprocess.call(['systemctl','start','--no-block','aura-avatar-ui.service'])
    result.update(status='ROLLED_BACK',error=str(exc))
result['camera_pid_after']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],universal_newlines=True).strip()
result['camera_preserved']=result['camera_pid_after']==camera_pid
(release/'deployment.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
'''
remote=remote.replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
result=ssh('python3 -',remote,timeout=220)
(HERE/'board_deployment.json').write_text(result,encoding='utf-8')
report=json.loads(result)
print(json.dumps(report,ensure_ascii=True,indent=2))
if report['status']!='DEPLOYED_STARTING':raise SystemExit(1)
