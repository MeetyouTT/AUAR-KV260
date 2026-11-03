#!/usr/bin/env python3
"""Build a pinned YOLO companion for the installed AURA UI/assets release."""
import hashlib
import json
from pathlib import Path
import zipfile

WORK = Path(__file__).resolve().parent
REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')


def sha(blob):return hashlib.sha256(blob).hexdigest()


def main():
    baseline = json.loads((WORK / 'baseline/manifest.json').read_text())
    assert baseline['update_id'] == 'aae0d9db5911b5e5'
    runtime = list(baseline['runtime_files']) + [
        'aura/board/vision/yolo_dpu.py', 'aura/board/vision/native/libaura_yolox.so',
        'aura/board/vision/native/yolox_bridge.cpp', 'aura/board/vision/native/build_yolox.py',
        'aura/config/board_camera_ui.cpu_yunet.json', 'aura/tests/framework/test_yolo_dpu.py',
        'aura/tests/fixtures/vision/person_bus.jpg']
    files = {name: (REPO / name[len('aura/'):]).read_bytes() for name in runtime}
    config = json.loads((WORK.parent / 'aura-board-ui-design-20261009/startup/config.json').read_text())
    for relative, record in baseline['files'].items():
        if relative.startswith('aura/') and relative in files and relative != 'aura/tools/board_avatar_gtk.py':
            config['component_sha256'][relative[len('aura/'):]] = sha(files[relative])
    for name in runtime:
        if name != 'aura/tools/board_avatar_gtk.py':
            config['component_sha256'][name[len('aura/'):]] = sha(files[name])
    config['gui_sha256'] = sha(files['aura/tools/board_avatar_gtk.py'])
    launcher = (REPO / 'scripts/board_ui_startup/launcher.py').read_bytes()
    configuration = (json.dumps(config, indent=2) + '\n').encode()
    release_id = sha(launcher + configuration)[:16]
    release = '/home/root/aura-ui-startup-20261009/releases/' + release_id
    unit = (REPO / 'scripts/board_ui_startup/aura-avatar-ui.service.in').read_text().replace('@INSTALL_DIR@', release).encode()
    files.update({'startup/launcher.py': launcher, 'startup/config.json': configuration,
                  'startup/aura-avatar-ui.service': unit, 'board_apply.py': (WORK / 'board_apply.py').read_bytes(),
                  'board_probe.py': (WORK / 'board_probe.py').read_bytes(),
                  'board_camera_control.py': (WORK / 'board_camera_control.py').read_bytes()})
    for name, blob in files.items():
        if name.endswith('.py'):compile(blob, name, 'exec')
        if name.endswith('.json'):json.loads(blob)
    update_id = sha(b''.join(name.encode() + bytes.fromhex(sha(blob)) for name, blob in sorted(files.items())))[:16]
    probe = json.loads((WORK / 'probe_manifest.json').read_text())
    seeds = {
        'aura/board/vision/native/libaura_yolox.so': probe['stage'] + '/libaura_yolox.so',
        'aura/tests/fixtures/vision/person_bus.jpg': probe['stage'] + '/bus-reference.jpg',
        'aura/board/vision/native/yolox_bridge.cpp': probe['stage'] + '/yolox_bridge.cpp',
        'aura/board/vision/native/build_yolox.py': probe['stage'] + '/build_yolox.py'}
    for name in files:
        if baseline['files'].get(name, {}).get('sha256') == sha(files[name]):
            seeds[name] = '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/ui-design-update-aae0d9db5911b5e5/payload/' + name
    manifest = {'kind': 'AURA_DPU_YOLOX_PERSON_UI_UPDATE', 'update_id': update_id,
        'startup_release_id': release_id, 'startup_release': release,
        'old_unit_sha256': baseline['files']['startup/aura-avatar-ui.service']['sha256'],
        'old_camera_unit_sha256': baseline['files']['aura/scripts/board_camera_ui/aura-camera-ui.service']['sha256'],
        'files': {name: {'bytes': len(blob), 'sha256': sha(blob)} for name, blob in files.items()},
        'runtime_files': {name: {'before_sha256': baseline['files'].get(name, {}).get('sha256')} for name in runtime},
        'verified_board_seeds': seeds,
        'model_dependency': json.loads(files['aura/config/board_camera_ui.json'])['yolo']}
    payload = dict(files, **{'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode()})
    archive = WORK / ('aura-yolo-update-' + update_id + '.zip')
    delta = WORK / ('aura-yolo-delta-' + update_id + '.zip')
    for path, names in [(archive, set(payload)), (delta, set(payload) - set(seeds))]:
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as stream:
            for name in sorted(names):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                stream.writestr(info, payload[name])
        with zipfile.ZipFile(path) as stream:
            assert stream.testzip() is None and set(stream.namelist()) == names
            for name in names:assert stream.read(name) == payload[name]
    metadata = {'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive.read_bytes()),
        'delta_archive': str(delta), 'delta_bytes': delta.stat().st_size, 'delta_sha256': sha(delta.read_bytes()),
        'update_id': update_id, 'startup_release_id': release_id, 'runtime_files': len(runtime),
        'payload_files': len(files), 'zip_readback_verified': True,
        'requires_installed_assets_and_pinned_board_model': True}
    (WORK / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (WORK / 'package_validation.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (WORK / 'startup').mkdir(exist_ok=True)
    for name in ('launcher.py', 'config.json', 'aura-avatar-ui.service'):
        (WORK / 'startup' / name).write_bytes(files['startup/' + name])
    print(json.dumps(metadata))


if __name__ == '__main__':main()
