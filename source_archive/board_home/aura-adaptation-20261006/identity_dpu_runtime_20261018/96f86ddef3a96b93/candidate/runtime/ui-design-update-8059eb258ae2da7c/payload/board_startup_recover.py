"""Replace only the owned startup release after verified missing-EDID failure."""
import json,subprocess,time,urllib.request
from pathlib import Path
from board_apply import ROOT,STAGE,MANIFEST,UNIT,api,atomic,protected,processes,run,sha,verify_payload

verify_payload()
assert sha(UNIT)==MANIFEST['old_unit_sha256']
for name in MANIFEST['runtime_files']:
    assert sha(ROOT/name)==MANIFEST['files'][name]['sha256'],name
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert Path('/sys/class/drm/card0-DP-1/status').read_text().strip()=='connected'
assert not Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
assert 'WaveShare WS170120' in run(['xinput','list','--name-only']).splitlines()
assert not processes().get('board_avatar_gtk.py'),'An active GUI requires the normal updater'
journal=run(['journalctl','-u',UNIT.name,'-n','25','--no-pager'])
assert 'Display startup timed out: Expected screen EDID not ready' in journal
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as s:camera=json.load(s)
assert camera['board_boot_id']==boot
before={'boot_id':boot,'processes':processes(),'protected':protected(),'camera':camera,
    'unit_sha256':sha(UNIT),'display':run(['xrandr','--current']),
    'settings':json.loads((ROOT/'avatar_user_settings.json').read_text())}
backup=STAGE/'startup-recovery-backup';backup.mkdir(exist_ok=False)
(backup/'before.json').write_text(json.dumps(before,indent=2)+'\n')
(backup/UNIT.name).write_bytes(UNIT.read_bytes())
run(['systemctl','stop',UNIT.name])
try:
    release=Path(MANIFEST['startup_release']);release.mkdir(exist_ok=False)
    for name in ('launcher.py','config.json','aura-avatar-ui.service'):
        atomic(release/name,(STAGE/'payload/startup'/name).read_bytes())
    preflight=run(['python3','-B',str(release/'launcher.py'),'--config',str(release/'config.json'),'--preflight'])
    atomic(UNIT,(release/UNIT.name).read_bytes())
    run(['systemctl','daemon-reload']);run(['systemctl','reset-failed',UNIT.name])
    run(['systemctl','--no-block','start',UNIT.name])
    end=time.monotonic()+70;state=None
    while time.monotonic()<end:
        try:
            state=api()
            if state.get('ui_runtime',{}).get('frame_visible'):break
        except OSError:pass
        time.sleep(.25)
    assert state and state['ui_runtime']['frame_visible'],'GUI did not become ready'
    launch=json.loads((ROOT/'launch.json').read_text());assert launch['boot_id']==boot
    assert protected()==before['protected']
    after=processes()
    for name in ('Xorg','dfx-mgrd'):assert after.get(name)==before['processes'].get(name),name
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as s:camera_after=json.load(s)
    assert camera_after['pid']==camera['pid']
    assert json.loads((ROOT/'avatar_user_settings.json').read_text())==before['settings']
    result={'startup_recovered':True,'update_id':MANIFEST['update_id'],'startup_release':str(release),
        'before':before,'launch':launch,'state':state,'camera_after':camera_after,'preflight':preflight,
        'display':run(['xrandr','--current']),'unit_sha256':sha(UNIT),
        'runtime_hashes':{name:sha(ROOT/name) for name in MANIFEST['runtime_files']}}
    (STAGE/'STARTUP_RECOVERED.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
except Exception:
    run(['systemctl','stop',UNIT.name]);atomic(UNIT,(backup/UNIT.name).read_bytes())
    run(['systemctl','daemon-reload']);run(['systemctl','--no-block','start',UNIT.name])
    raise
