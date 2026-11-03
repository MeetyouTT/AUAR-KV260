"""Build a startup-only release from the actual installed component manifest."""
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
SOURCE = ROOT/'scripts/board_ui_startup'
INVENTORY = Path('/home/ghmd/aura-asr-integration-20261016/evidence/20261018T042411.183463Z-display-startup-inventory')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    old = json.loads((INVENTORY/'response.json').read_text())
    assert (INVENTORY/'installed_launcher.py').read_bytes() == (WORK/'before/scripts/board_ui_startup/launcher.py').read_bytes()
    # Preserve the current GUI, ASR and hotplug-fix hashes instead of copying
    # the older source-tree configuration's component list.
    config = json.loads((INVENTORY/'installed_config.json').read_text())
    config.update(edid_grace_seconds=15, display_stable_seconds=3,
                  startup_display_retrain=True, display_retrain_off_seconds=1,
                  display_recovery_marker='/run/aura-display-startup.json')
    config_data = (json.dumps(config, ensure_ascii=False, indent=2)+'\n').encode()
    launcher = (SOURCE/'launcher.py').read_bytes()
    old_release = str(Path(old['config_path']).parent)
    old_unit = (INVENTORY/'installed_ui.service').read_bytes()
    release_id = sha(launcher+config_data+old_unit)[:16]
    release = '/home/root/aura-ui-startup-20261009/releases/'+release_id
    assert old_unit.count(old_release.encode()) == 2
    unit = old_unit.replace(old_release.encode(), release.encode())
    payload = {'launcher.py':launcher, 'config.json':config_data, 'aura-avatar-ui.service':unit}
    for name in ('test_display_fallback.py', 'test_display_startup.py'):
        payload[name] = (SOURCE/name).read_bytes()
    manifest = {
        'release_id':release_id, 'release':release,
        'expected_boot_id':old['boot_id'], 'expected_active_release':old_release,
        'old_unit_sha256':sha(old_unit), 'old_config_sha256':sha((INVENTORY/'installed_config.json').read_bytes()),
        'old_launcher_sha256':sha((INVENTORY/'installed_launcher.py').read_bytes()),
        'files':{name:{'bytes':len(data), 'sha256':sha(data)} for name,data in payload.items()},
        'activation':'next_service_start_only; do not restart current UI or display',
    }
    candidate = WORK/'candidate';candidate.mkdir(exist_ok=True)
    for name,data in payload.items():
        (candidate/name).write_bytes(data)
    (candidate/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    tests = subprocess.run(['python3','-B','-m','unittest','test_display_fallback','test_display_startup','-v'],
                           cwd=str(candidate), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,text=True)
    (WORK/'host_display_tests.log').write_text(tests.stdout)
    assert tests.returncode == 0, tests.stdout
    assert 'Ran 17 tests' in tests.stdout, tests.stdout
    for name,data in payload.items():
        if name.endswith('.py'):compile(data,name,'exec')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(candidate.iterdir()):z.writestr(p.name,p.read_bytes())
    blob=buffer.getvalue()
    archive=WORK/('display-startup-'+release_id+'.zip');archive.write_bytes(blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert z.testzip() is None
        for name,row in manifest['files'].items():
            data=z.read(name);assert len(data)==row['bytes'] and sha(data)==row['sha256']
    script=(WORK/'board_install_template.py').read_text().replace('BUNDLE_BASE64',base64.b64encode(blob).decode())
    helper=Path('/home/ghmd/aura-asr-integration-20261016/board_display_install.py')
    helper.write_text(script)
    (WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    summary={'release_id':release_id,'zip':str(archive),'zip_sha256':sha(blob),'zip_bytes':len(blob),
             'host_tests':17,'host_test_exit_code':tests.returncode,'files':len(payload)}
    (WORK/'build_validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
