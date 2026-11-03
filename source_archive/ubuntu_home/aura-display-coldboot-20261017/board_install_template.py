"""Install a validated startup release; leave all running services untouched."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile

blob=base64.b64decode('BUNDLE_BASE64',validate=True)
archive=zipfile.ZipFile(io.BytesIO(blob))
manifest=json.loads(archive.read('manifest.json'))
release=Path(manifest['release'])
stage=Path('/home/root/aura-display-coldboot-20261017')/('release-'+manifest['release_id'])
unit=Path('/etc/systemd/system/aura-avatar-ui.service')
old_release=Path(manifest['expected_active_release'])
assert release.parent==old_release.parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=25)
    if p.returncode:raise RuntimeError(str(args)+': '+p.stdout[-2500:])
    return p.stdout


def read_api(port,path):
    with urllib.request.urlopen('http://127.0.0.1:%d/%s'%(port,path),timeout=3) as r:return json.load(r)


def snapshot():
    launch=json.loads(Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/launch.json').read_text())
    pid=int(run(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).strip())
    ui=read_api(8783,'api/state');camera=read_api(8790,'health')
    paths=['/lib/systemd/system/xserver-nodm.service','/etc/default/xserver-nodm',
           '/etc/systemd/system/aura-camera-ui.service','/etc/modules-load.d/aura-touch.conf','/etc/vart.conf']
    return {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'supervisor_pid':pid,'gui_pid':launch['pid'],
            'active_supervisor_args':Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0'),
            'camera_pid':camera['pid'],'camera_epoch':camera['service_epoch'],
            'ui_settings':ui['ui_settings'],'phase':ui['phase'],
            'protected':{p:sha(p) for p in paths}}


def atomic(path,data):
    temporary=path.with_name(path.name+'.display-new-'+manifest['release_id'])
    with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(str(temporary),str(path))


before=snapshot()
assert before['boot_id']==manifest['expected_boot_id']
assert sha(unit)==manifest['old_unit_sha256']
assert sha(old_release/'config.json')==manifest['old_config_sha256']
assert sha(old_release/'launcher.py')==manifest['old_launcher_sha256']
assert str(old_release/'launcher.py') in before['active_supervisor_args']
assert not release.exists() and not stage.exists()
for name,row in manifest['files'].items():
    assert Path(name).name==name
    data=archive.read(name)
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    if name.endswith('.py'):compile(data,name,'exec')
stage.mkdir(parents=True);backup=stage/'backup';backup.mkdir()
(backup/'before.json').write_text(json.dumps(before,indent=2)+'\n')
old_unit=unit.read_bytes();(backup/'ui.service').write_bytes(old_unit)
for name in ('config.json','launcher.py'):(backup/name).write_bytes((old_release/name).read_bytes())
release.mkdir()
for name in manifest['files']:(release/name).write_bytes(archive.read(name))
(release/'release_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
tests=run(['python3','-B','-m','unittest','discover','-s',str(release),'-p','test_display*.py','-v'])
(stage/'board_display_tests.log').write_text(tests)
assert 'Ran 17 tests' in tests
preflight=run(['python3','-B',str(release/'launcher.py'),'--config',str(release/'config.json'),'--preflight'])
changed=False
try:
    atomic(unit,(release/'aura-avatar-ui.service').read_bytes());changed=True
    run(['systemctl','daemon-reload'])
    after=snapshot()
    for key in ('boot_id','supervisor_pid','gui_pid','active_supervisor_args','camera_pid','camera_epoch','protected'):
        assert after[key]==before[key],key
    assert after['ui_settings']['volume']==before['ui_settings']['volume']
    assert after['ui_settings']['muted']==before['ui_settings']['muted']
    assert run(['systemctl','is-enabled','aura-avatar-ui.service']).strip()=='enabled'
    assert run(['systemctl','is-active','aura-avatar-ui.service']).strip()=='active'
    result={'status':'INSTALLED_FOR_NEXT_START_CURRENT_UI_UNCHANGED','release_id':manifest['release_id'],
            'release':str(release),'before':before,'after':after,'board_tests':17,'preflight':preflight,
            'installed_unit_sha256':sha(unit),'file_hashes':{n:sha(release/n) for n in manifest['files']},
            'cold_boot_verified':False,'physical_panel_verified':False,'backup':str(backup)}
    (stage/'APPLIED.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
except Exception:
    if changed:
        atomic(unit,old_unit);run(['systemctl','daemon-reload'])
    raise
