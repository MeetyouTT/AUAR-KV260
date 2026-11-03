"""Update the owned GUI with exact before hashes, backups and bounded rollback."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

STAGE = Path(__file__).resolve().parent.parent
PAYLOAD = STAGE/'payload'
MANIFEST = json.loads((PAYLOAD/'manifest.json').read_text())
ROOT = Path(MANIFEST['runtime'])
UNIT = Path('/etc/systemd/system/aura-avatar-ui.service')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args,timeout=35):
    p=subprocess.run(args,cwd=str(ROOT/'aura'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     text=True,timeout=timeout,env=dict(os.environ,DISPLAY=':0'))
    if p.returncode:raise RuntimeError(str(args)+': '+p.stdout[-2500:])
    return p.stdout


def state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:return json.load(r)


def camera():
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:return json.load(r)


def protected():
    paths=['/lib/systemd/system/xserver-nodm.service','/etc/default/xserver-nodm',
           '/etc/systemd/system/aura-camera-ui.service','/etc/modules-load.d/aura-touch.conf',
           '/etc/vart.conf']
    return {p:sha(p) for p in paths}


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.record-new-'+MANIFEST['update_id'])
    with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(str(temporary),str(path))


def inspect():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==MANIFEST['expected_boot_id']
    assert sha(UNIT)==MANIFEST['old_unit_sha256']
    for rel,row in MANIFEST['runtime_files'].items():
        p=ROOT/'aura'/rel
        assert not p.is_symlink()
        if row['before_sha256'] is None:assert not p.exists(),rel
        else:assert p.is_file() and sha(p)==row['before_sha256'],rel
    current=state()
    assert current['phase']=='IDLE' and not current['playing'] and not current['paused']
    assert not current['ui_settings']['pending']
    assert not current.get('avatar_command_pending')
    assert current.get('local_recording',{}).get('can_start')
    assert current.get('local_recording',{}).get('state') != 'RECORDING'
    c=camera()
    return {'camera':c,'protected':protected(),'ui':current,
            'saved_settings':json.loads((ROOT/'avatar_user_settings.json').read_text()),
            'saved_connection':json.loads((ROOT/'avatar_service_settings.json').read_text())}


def restore():
    backup=STAGE/'backup'
    for rel,row in MANIFEST['runtime_files'].items():
        p=ROOT/'aura'/rel;saved=backup/'aura'/rel
        if saved.exists():atomic(p,saved.read_bytes())
        elif p.exists():
            assert sha(p)==MANIFEST['files']['aura/'+rel]['sha256']
            p.unlink()  # Only a file created by this exact update, with matching bytes.
    atomic(UNIT,(backup/'ui.service').read_bytes())
    run(['systemctl','daemon-reload'])
    run(['systemctl','reset-failed',UNIT.name])
    run(['systemctl','--no-block','start',UNIT.name])
    return {'restored_unit':sha(UNIT),'backup':str(backup)}


def main():
    for rel,row in MANIFEST['files'].items():
        p=PAYLOAD/rel
        assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],rel
        if p.suffix=='.py':compile(p.read_bytes(),str(p),'exec')
    before=inspect()
    backup=STAGE/'backup';backup.mkdir(exist_ok=False)
    (backup/'before.json').write_text(json.dumps(before,indent=2)+'\n')
    shutil.copy2(str(UNIT),str(backup/'ui.service'))
    for rel,row in MANIFEST['runtime_files'].items():
        p=ROOT/'aura'/rel
        if p.exists():
            target=backup/'aura'/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(str(p),str(target))
    try:
        run(['systemctl','stop',UNIT.name])
        for rel in MANIFEST['runtime_files']:atomic(ROOT/'aura'/rel,(PAYLOAD/'aura'/rel).read_bytes())
        tests=run(['python3','-B','-s','-m','unittest','tests.framework.test_board_recording',
                   'tests.framework.test_stage_bridge','tests.framework.test_board_avatar_worker'],timeout=25)
        (STAGE/'native-tests.log').write_text(tests)
        resources=run(['python3','-B','tools/board_avatar_preflight.py','--resources-only'],timeout=25)
        assert json.loads(resources)['status']=='PASS'
        release=Path(MANIFEST['startup_release']);release.mkdir(exist_ok=False)
        for name in ('launcher.py','config.json','aura-avatar-ui.service'):
            atomic(release/name,(PAYLOAD/'startup'/name).read_bytes())
        preflight=run(['python3','-B',str(release/'launcher.py'),'--config',str(release/'config.json'),'--preflight'],timeout=25)
        atomic(UNIT,(release/'aura-avatar-ui.service').read_bytes())
        run(['systemctl','daemon-reload'])
        assert protected()==before['protected']
        assert json.loads((ROOT/'avatar_user_settings.json').read_text())==before['saved_settings']
        assert json.loads((ROOT/'avatar_service_settings.json').read_text())==before['saved_connection']
        after=camera()
        assert (after['pid'],after['service_epoch'])==(before['camera']['pid'],before['camera']['service_epoch'])
        run(['systemctl','reset-failed',UNIT.name])
        run(['systemctl','--no-block','start',UNIT.name])
        result={'status':'START_REQUESTED','update_id':MANIFEST['update_id'],'startup_release':str(release),
                'backup':str(backup),'native_tests':tests,'resources_status':'PASS','preflight':preflight,
                'camera_before':before['camera'],'camera_after':after,
                'runtime_files':{rel:sha(ROOT/'aura'/rel) for rel in MANIFEST['runtime_files']}}
        (STAGE/'APPLIED.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    except Exception as exc:
        run(['systemctl','stop',UNIT.name])
        result={'status':'FAILED_WITH_ROLLBACK','error':str(exc),'rollback':restore()}
        (STAGE/'FAILED.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
        raise


if __name__=='__main__':main()
