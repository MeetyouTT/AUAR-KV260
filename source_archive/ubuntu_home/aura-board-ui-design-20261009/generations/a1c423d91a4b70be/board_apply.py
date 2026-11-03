#!/usr/bin/env python3
"""Guarded update of only the owned UI; back up before stopping its service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
STAGE = Path(__file__).resolve().parent.parent
PAYLOAD = STAGE/'payload'
MANIFEST = json.loads((PAYLOAD/'manifest.json').read_text())
UNIT = Path('/etc/systemd/system/aura-avatar-ui.service')
ENV = dict(os.environ,DISPLAY=':0',PYTHONUNBUFFERED='1')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, timeout=40):
    result = subprocess.run(args,cwd=str(ROOT/'aura'),env=ENV,stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError(str(args)+': '+result.stdout[-3000:])
    return result.stdout


def api(value=None):
    base = 'http://127.0.0.1:8783'
    request = base+'/api/state' if value is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=10) as stream:return json.load(stream)


def atomic(path, data):
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_name(path.name+'.ui-new-'+MANIFEST['update_id'])
    with temp.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.replace(str(temp),str(path))


def protected():
    return {name:sha(name) for name in ('/lib/systemd/system/xserver-nodm.service',
        '/etc/default/xserver-nodm','/etc/modules-load.d/aura-touch.conf',
        '/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko')}


def processes():
    result = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args = (p/'cmdline').read_bytes().decode(errors='replace').split(chr(0))
            stat = (p/'stat').read_text().split(') ')[1].split()
        except OSError:continue
        for name in ('Xorg','dfx-mgrd','realtime_vision.py','board_avatar_gtk.py','gstreamer_audio_worker.py'):
            if any(Path(a).name == name for a in args if a):
                result.setdefault(name,[]).append({'pid':int(p.name),'start_ticks':stat[19],'ppid':int(stat[1])})
    return result


def verify_payload():
    for name,row in MANIFEST['files'].items():
        path = PAYLOAD/name
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],name
        if name.endswith('.py'):compile(path.read_bytes(),name,'exec')


def inspect():
    missing = []
    for rel,row in MANIFEST['runtime_files'].items():
        path = ROOT/rel
        if row['before_sha256']:
            assert path.is_file() and not path.is_symlink() and sha(path) == row['before_sha256'],rel
        else:
            assert not path.exists() and not path.is_symlink(),rel
            missing.append(rel)
    assert sha(UNIT) == MANIFEST['old_unit_sha256']
    state = api();info = json.loads((ROOT/'launch.json').read_text())
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert info['boot_id'] == boot
    assert str(ROOT/'aura/tools/board_avatar_gtk.py').encode() in (Path('/proc')/str(info['pid'])/'cmdline').read_bytes().split(b'\0')
    assert run(['systemctl','show',UNIT.name,'-p','MainPID','--value']).strip() == str(info['supervisor_pid'])
    assert state['phase'] == 'IDLE' and not state['playing'] and not state['paused']
    assert not state['ui_settings']['pending']
    return {'boot_id':boot,'launch':info,'state':state,'new_runtime_files':missing,
            'protected':protected(),'processes':processes(),'free_bytes':shutil.disk_usage(str(ROOT)).free,
            'saved_preferences':json.loads((ROOT/'avatar_user_settings.json').read_text())}


def restore():
    backup = STAGE/'backup'
    for rel,row in MANIFEST['runtime_files'].items():
        path = ROOT/rel;saved = backup/rel
        if saved.exists():atomic(path,saved.read_bytes())
        elif path.exists():
            assert sha(path) == MANIFEST['files'][rel]['sha256'],rel
            path.unlink()  # Only files created by this exact update, with matching SHA.
    atomic(UNIT,(backup/'aura-avatar-ui.service').read_bytes())
    run(['systemctl','daemon-reload'])
    run(['systemctl','reset-failed',UNIT.name])
    run(['systemctl','--no-block','start',UNIT.name])
    return {'rollback_requested':True,'restored_unit_sha256':sha(UNIT),'backup':str(backup)}


def apply():
    before = inspect()
    backup = STAGE/'backup';backup.mkdir(exist_ok=False)
    (backup/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
    for rel,row in MANIFEST['runtime_files'].items():
        path = ROOT/rel
        if path.exists():
            target = backup/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(str(path),str(target))
    for name in ('avatar_user_settings.json','launch.json','avatar_service_settings.json'):
        path = ROOT/name
        if path.exists():shutil.copy2(str(path),str(backup/name))
    shutil.copy2(str(UNIT),str(backup/UNIT.name))
    previous_report = api({'type':'save_evidence'})
    assert previous_report['ok']
    (backup/'previous-report.json').write_text(json.dumps(previous_report,indent=2)+'\n')
    state = api()
    assert state['phase'] == 'IDLE' and not state['playing'] and not state['paused'] and not state['ui_settings']['pending']
    run(['systemctl','stop',UNIT.name])
    try:
        assert run(['systemctl','show',UNIT.name,'-p','MainPID','--value']).strip() == '0'
        for rel in MANIFEST['runtime_files']:
            atomic(ROOT/rel,(PAYLOAD/rel).read_bytes())
        logs = []
        for pattern in ('test_board_ui_services.py','test_board_ui_settings.py'):
            logs.append(run(['python3','-B','-m','unittest','discover','-s','tests/framework','-p',pattern,'-v']))
        (STAGE/'native-tests.log').write_text('\n'.join(logs))
        resources = json.loads(run(['python3','-B','tools/board_avatar_gtk.py','--check'],timeout=60))
        assert resources['status'] == 'PASS' and resources['device_opened'] is False
        (STAGE/'resource-check.json').write_text(json.dumps(resources,indent=2)+'\n')
        release = Path(MANIFEST['startup_release']);release.mkdir(exist_ok=False)
        for name in ('launcher.py','config.json','aura-avatar-ui.service'):
            atomic(release/name,(PAYLOAD/'startup'/name).read_bytes())
        preflight = run(['python3','-B',str(release/'launcher.py'),'--config',str(release/'config.json'),'--preflight'])
        atomic(UNIT,(release/UNIT.name).read_bytes())
        run(['systemctl','daemon-reload'])
        assert run(['systemctl','is-enabled',UNIT.name]).strip() == 'enabled'
        assert protected() == before['protected']
        run(['systemctl','reset-failed',UNIT.name])
        run(['systemctl','--no-block','start',UNIT.name])
        result = {'deployment_requested':True,'update_id':MANIFEST['update_id'],
                  'startup_release':str(release),'before':before,'backup':str(backup),
                  'native_test_count':35,'resources_status':resources['status'],'preflight':preflight,
                  'runtime_files':{rel:sha(ROOT/rel) for rel in MANIFEST['runtime_files']}}
        (STAGE/'APPLIED.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False))
    except Exception as exc:
        result = {'error':type(exc).__name__+': '+str(exc),'recovery':restore()}
        (STAGE/'FAILED.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result));raise


def status():
    try:state = api()
    except Exception as exc:state = {'api_error':str(exc)}
    info = json.loads((ROOT/'launch.json').read_text())
    log = Path(info['log']).read_text(errors='replace')[-5000:]
    print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'service':run(['systemctl','show',UNIT.name,'-p','ActiveState','-p','SubState','-p','Result',
                       '-p','NRestarts','-p','MainPID','-p','UnitFileState']),
        'state':state,'launch':info,'log':log,'protected':protected(),'processes':processes(),
        'unit_sha256':sha(UNIT),'saved_preferences':json.loads((ROOT/'avatar_user_settings.json').read_text()),
        'display':run(['xrandr','--current']),'touch':run(['xinput','list','--long','WaveShare WS170120'])},ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('inspect','apply','status','rollback'),required=True)
    args = parser.parse_args();verify_payload()
    if args.phase == 'inspect':print(json.dumps(inspect(),ensure_ascii=False))
    elif args.phase == 'apply':apply()
    elif args.phase == 'status':status()
    else:
        assert sha(UNIT) == MANIFEST['files']['startup/aura-avatar-ui.service']['sha256']
        run(['systemctl','stop',UNIT.name]);print(json.dumps(restore()))


if __name__ == '__main__':main()
