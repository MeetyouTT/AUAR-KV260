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

SHADOW_PINS = {'face_edge_control.py': '589293a34edec2bc57f2323250e52180717e6ae6495efe1390a11da3da4bb3a3', 'face_source.py': 'd89d0c8c16a8e84f5a725954d7b3166f5329b6ebb44c8ea82fdc40e1930cfe9b', 'face_flow.py': '633978889c63237b4244c2d0421ade79d25d91613f3521eb4b102536661aca41', 'motion_stream.py': 'd0da6d063851ed2bbe8c0fe68fbd6c42d4afee02c3d0d73db9bcc01339f71c6a', 'camera_wrapper.py': '065c465e0ad0d8cf3ada4b69dcc422a4f85a286b1a7be1536e29d4aeac562df8', 'run_face_shadow.py': '8b25878614e16eff530e9f2bb5b5984c5a2f0e86d7ea2f4d7c86e79697b4b6c1', 'face_motion.py': '031c6944e676d1c914538092f1bdf4af9100cd9357044327db9b2c025e89a6bc', 'run_face_motion.py': 'c1d51a1b8ac8808088fecf5c91fc1e1aa31f5eebb5047611dad86044275bfd90', 'face_pan_controls.py': '6147f157378f3e99ffb4d0629aa707193a3fa27587dae57231d541ed6b6d7056', 'config.json': 'e325bf7ba17258bd0c381fc3c4b9cf3ccd89611aed3d6988c38b84f4bf969a0d'}


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
    shadow_root = ops_root / 'pan-face-edge-v4'
    meta = json.loads((ops_root / 'meta.json').read_text())
    pins = meta.get('source_pins', {})
    native_pin = next((value for name, value in pins.items()
                       if Path(name).name == 'native_entry.py'), None)
    original_entry = ops_root / 'native_entry.py'
    if not native_pin or digest(original_entry) != native_pin:
        raise RuntimeError('Existing native entry does not match its source pin')

    aura = Path(meta['candidate_root']) / 'aura'
    camera_entry = aura / 'board/vision/ui_camera_service.py'
    motion_wrapper = shadow_root / 'camera_wrapper.py'
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
