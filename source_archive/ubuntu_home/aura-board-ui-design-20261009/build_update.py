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
    baseline = json.loads((WORK/'generations/49e441bea05c3d3f/manifest.json').read_text())
    runtime = ['aura/tools/board_avatar_gtk.py','aura/board/interaction/ui_contract.py',
        'aura/board/interaction/ui_services.py','aura/config/board_ui_services.json',
        'aura/ui/board_touch_layout.json','aura/tests/framework/test_board_ui_services.py',
        'aura/common/schemas/board_ui_snapshot.schema.json','aura/common/schemas/board_ui_command.schema.json',
        'aura/common/schemas/board_ui_ack.schema.json','aura/tools/board_screen_capture.py',
        'aura/board/vision/ui_camera_service.py','aura/config/board_camera_ui.json',
        'aura/scripts/board_camera_ui/aura-camera-ui.service','aura/tests/framework/test_camera_ui_service.py',
        'aura/tools/board_avatar_worker.py','aura/tests/framework/test_board_avatar_worker.py',
        'aura/tools/board_camera_preview.py','aura/board/vision/local_preview.py',
        'aura/tests/framework/test_local_camera_preview.py']
    files = {name:(REPO/name[len('aura/'):]).read_bytes() for name in runtime}
    launcher = (REPO/'scripts/board_ui_startup/launcher.py').read_text()
    assert 'component_sha256' in launcher and "'event': 'cancel'" in launcher
    config = json.loads((WORK/'before/scripts/board_ui_startup/config.json').read_text())
    config['gui_sha256'] = sha(files['aura/tools/board_avatar_gtk.py'])
    config['verified_timing_fallback'] = ['49.000','1024','1072','1168','1312','600','603','613','624','-HSync','-VSync']
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
    for name in ('board_apply.py','board_probe.py','fixture_provider.py','board_camera_control.py','board_startup_recover.py'):
        files[name] = (WORK/name).read_bytes()
    for name,data in files.items():
        if name.endswith('.py'):compile(data,name,'exec')
        elif name.endswith('.json'):json.loads(data)
    update_id = sha(b''.join(name.encode()+bytes.fromhex(sha(data)) for name,data in sorted(files.items())))[:16]
    manifest = {'kind':'AURA_TOUCHSCREEN_UI_AND_ADAPTER_UPDATE','update_id':update_id,
                'startup_release_id':release_id,'startup_release':release,
                'old_unit_sha256':baseline['files']['startup/aura-avatar-ui.service']['sha256'],
                'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in files.items()},
                'runtime_files':{name:{'before_sha256':baseline['files'].get(name,{}).get('sha256')} for name in runtime}}
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
