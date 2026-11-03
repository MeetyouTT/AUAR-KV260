"""Add the pinned read-only feed while preserving the existing native entry."""
import hashlib
import json
from pathlib import Path
import runpy
import sys


APP_PINS = {
    'board/vision/ui_camera_service.py': '9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df',
    'board/motion/camera_feed.py': '2bf8983cf195af94d4a6faefc48eefdbc9b2a02ffcd863f9ffac006dc495f3e7',
    'common/motion_observation.py': 'c676a81093793ee7046d1937c56478efe27a94505c9fd62696e82fc426acf9dc',
    'tools/board_camera_motion.py': '1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005',
}

SHADOW_PINS = {
    'follow.py': '22fa85bed11e4a4ae5ff9db6d747fbeae474f6d871d91a169fd93404e84daf7b',
    'run_shadow.py': '73cc1fa4e79f1384c8174bda5ccd59244f5f1918f6019fdd20c946920b1a4e9d',
    'config.json': 'e21506deb5f97ee28f1eaa06eedf9f457864894a4cc8f1041228f7ce31dba8b4',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hook_camera_run(runpy_module, camera_entry, motion_wrapper):
    original = runpy_module.run_path
    camera_entry = Path(camera_entry).resolve()
    motion_wrapper = Path(motion_wrapper).resolve()

    def dispatch(path, *args, **kwargs):
        if (Path(path).resolve() == camera_entry
                and kwargs.get('run_name') == '__main__'):
            sys.argv[0] = str(motion_wrapper)
            return original(str(motion_wrapper), *args, **kwargs)
        return original(path, *args, **kwargs)

    runpy_module.run_path = dispatch
    return original


def main():
    ops_root = Path(__file__).resolve().parent
    shadow_root = ops_root / 'pan-follow-shadow-live'
    meta = json.loads((ops_root / 'meta.json').read_text())
    pins = meta.get('source_pins', {})
    native_pin = next((value for name, value in pins.items()
                       if Path(name).name == 'native_entry.py'), None)
    original_entry = ops_root / 'native_entry.py'
    if not native_pin or digest(original_entry) != native_pin:
        raise RuntimeError('Existing native entry does not match its source pin')

    aura = Path(meta['candidate_root']) / 'aura'
    camera_entry = aura / 'board/vision/ui_camera_service.py'
    motion_wrapper = aura / 'tools/board_camera_motion.py'
    if digest(camera_entry) != meta['candidate_ui_sha256']:
        raise RuntimeError('Camera source pin changed')
    for relative, expected in APP_PINS.items():
        path = aura / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError('Read-only feed source pin changed: ' + relative)
    for relative, expected in SHADOW_PINS.items():
        path = shadow_root / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError('Shadow release pin changed: ' + relative)

    sys.argv = [str(original_entry)]
    original = hook_camera_run(runpy, camera_entry, motion_wrapper)
    try:
        original(str(original_entry), run_name='__main__')
    finally:
        runpy.run_path = original


if __name__ == '__main__':
    main()
