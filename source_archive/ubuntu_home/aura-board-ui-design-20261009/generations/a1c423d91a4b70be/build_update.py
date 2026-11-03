#!/usr/bin/env python3
"""Build a small, hash-pinned companion update for the already installed assets."""
import hashlib
import json
from pathlib import Path
import zipfile

WORK = Path(__file__).resolve().parent
REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    runtime = ['aura/tools/board_avatar_gtk.py','aura/board/interaction/ui_contract.py',
        'aura/board/interaction/ui_services.py','aura/config/board_ui_services.json',
        'aura/ui/board_touch_layout.json','aura/tests/framework/test_board_ui_services.py',
        'aura/common/schemas/board_ui_snapshot.schema.json','aura/common/schemas/board_ui_command.schema.json',
        'aura/common/schemas/board_ui_ack.schema.json']
    files = {name:(REPO/name[len('aura/'):]).read_bytes() for name in runtime}
    launcher = (WORK/'before/scripts/board_ui_startup/launcher.py').read_text()
    old = "    if os.uname().release != config['kernel_release']:"
    replacement = "    for relative, expected in config.get('component_sha256', {}).items():\n        component = root/'aura'/relative\n        if hashlib.sha256(component.read_bytes()).hexdigest() != expected:\n            raise ValueError('UI component SHA256 mismatch: '+relative)\n"+old
    assert launcher.count(old) == 1
    launcher = launcher.replace(old,replacement)
    old = "({'type': 'cancel'}, {'type': 'save_evidence'})"
    assert launcher.count(old) == 1
    launcher = launcher.replace(old,"({'type': 'event', 'event': 'cancel'}, {'type': 'save_evidence'})")
    config = json.loads((WORK/'before/scripts/board_ui_startup/config.json').read_text())
    config['gui_sha256'] = sha(files['aura/tools/board_avatar_gtk.py'])
    config['component_sha256'] = {name[len('aura/'):]:sha(data) for name,data in files.items()
                                 if name != 'aura/tools/board_avatar_gtk.py'}
    for relative in ('tools/realtime_bridge.py','tools/board_ui_settings.py','ui/ui_layout_spec.json','ui/ui_tokens.json'):
        config['component_sha256'][relative] = sha((REPO/relative).read_bytes())
    source = launcher.encode();configuration = (json.dumps(config,indent=2)+'\n').encode()
    release_id = sha(source+configuration)[:16]
    release = '/home/root/aura-ui-startup-20261009/releases/'+release_id
    template = (REPO/'scripts/board_ui_startup/aura-avatar-ui.service.in').read_text()
    unit = template.replace('@INSTALL_DIR@',release).encode()
    files.update({'startup/launcher.py':source,'startup/config.json':configuration,'startup/aura-avatar-ui.service':unit})
    for name in ('board_apply.py','board_probe.py','fixture_provider.py'):
        files[name] = (WORK/name).read_bytes()
    for name,data in files.items():
        if name.endswith('.py'):compile(data,name,'exec')
        elif name.endswith('.json'):json.loads(data)
    update_id = sha(b''.join(name.encode()+bytes.fromhex(sha(data)) for name,data in sorted(files.items())))[:16]
    manifest = {'kind':'AURA_TOUCHSCREEN_UI_AND_ADAPTER_UPDATE','update_id':update_id,
                'startup_release_id':release_id,'startup_release':release,
                'old_unit_sha256':'cb63edc9c50adbe93c9ee6f9ff572ff3ff8ed79238db8b0f72645d9f4ebcfed0',
                'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in files.items()},
                'runtime_files':{name:{'before_sha256':sha((WORK/'before/tools/board_avatar_gtk.py').read_bytes())
                                      if name == 'aura/tools/board_avatar_gtk.py' else None} for name in runtime}}
    payload = dict(files,**{'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()})
    archive = WORK/('aura-board-ui-update-'+update_id+'.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as out:
        for name,data in sorted(payload.items()):
            info = zipfile.ZipInfo(name,date_time=(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            out.writestr(info,data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist()) == set(payload)
        for name,data in payload.items():assert z.read(name) == data
    (WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    metadata = {'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),
                'update_id':update_id,'startup_release_id':release_id,'payload_count':len(files),
                'runtime_files':len(runtime),'zip_readback_verified':True}
    (WORK/'package_validation.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (WORK/'startup').mkdir(exist_ok=True)
    for name in ('launcher.py','config.json','aura-avatar-ui.service'):
        (WORK/'startup'/name).write_bytes(files['startup/'+name])
    print(json.dumps(metadata))


if __name__ == '__main__':main()
