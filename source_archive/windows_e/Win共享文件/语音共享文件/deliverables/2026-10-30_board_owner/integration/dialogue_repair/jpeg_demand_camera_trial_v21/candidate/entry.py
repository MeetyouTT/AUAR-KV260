"""Pinned JPEG-only overlay over the original protected camera entry.

Static verification opens only explicitly pinned source and metadata files.
The root-owned serial trial remains responsible for the sole-owner lifecycle.
"""
import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import sys
import types


OPS = '/home/root/aura-native-live-20261024/ops/be72669aa53de735'
SOURCE_ROOT = '/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura'
BASE_ENTRY = OPS + '/pan-face-edge-v5/face-source-v17/entry.py'
BASE_MANIFEST = OPS + '/pan-face-edge-v5/face-source-v17/deployment-manifest.json'
DISPATCH_ENTRY = OPS + '/pan-face-edge-v5/native-operator-v1/native_entry_operator.py'
OPERATOR_MANIFEST = OPS + '/pan-face-edge-v5/native-operator-v1/runtime-manifest.json'
PAN_ENTRY = OPS + '/native_entry_pan_face_v5.py'
ORIGINAL_CAMERA = SOURCE_ROOT + '/board/vision/ui_camera_service.py'
CAMERA_BEFORE = '9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
CAMERA_AFTER = '44b02084cb5e80b12349892183b08e02563c4447e75c5e05276d52786b8a55c4'
MODULE_NAME = 'board.vision.ui_camera_service'
POLICY = {
    'change': 'on_demand_JPEG_only',
    'dependency_root': SOURCE_ROOT,
    'original_camera_source_sha256': CAMERA_BEFORE,
    'candidate_camera_source_sha256': CAMERA_AFTER,
    'jpeg_quality': 72,
    'jpeg_limit_bytes': 262144,
    'preview_ring_entries': 8,
    'preview_ttl_ms': 1000,
    'raw_preview_ttl_ms': 250,
    'face_period_ms': 100,
    'optical_flow': True,
}
REQUIRED = {
    BASE_ENTRY: 'f26be22cb640bf44a1bd81b66bb3fa014f5b847b13320781836bf3f173387623',
    BASE_MANIFEST: '84d7359f18a5a98aa5dabba967c4ededf5e35d0c43153166fc6998729a30219c',
    DISPATCH_ENTRY: '0576a388e2c17174b4102665602aa42fbf078a3f016bdfb641c269571ce13943',
    PAN_ENTRY: '288f6b7b56702edf45b432686db4f77b156408c0b3f78fd31c05edb33df971c4',
    OPS + '/native_entry.py': '839df536696d16c3f538bb158edee80614fb0cef55def64d7e7849d412fa30d4',
    OPS + '/meta.json': 'ff35a462bd83b854a85439e7a226d5b7ba6069d5694e9d65ac95b407a7962ebe',
    OPERATOR_MANIFEST: '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad',
    ORIGINAL_CAMERA: CAMERA_BEFORE,
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate manifest key')
        result[key] = value
    return result


def read_static(name):
    target = Path(name)
    if target.is_symlink() or target.resolve() != target or not target.is_file():
        raise ValueError('Pinned source path redirected or unavailable')
    return target.read_bytes()


def inherited_subset(inherited, expected):
    if not isinstance(expected, dict) or any(inherited.get(name) != value for name, value in expected.items()):
        raise ValueError('Inherited source closure incomplete or changed')


def verify(root, expected_manifest_sha256, *, reader=read_static):
    root = Path(root).resolve()
    if not sha(expected_manifest_sha256):
        raise ValueError('Explicit candidate manifest SHA required')
    raw = reader(str(root / 'candidate-manifest.json'))
    if len(raw) > 262144 or digest(raw) != expected_manifest_sha256:
        raise ValueError('Candidate manifest SHA mismatch')
    value = json.loads(raw, object_pairs_hook=unique)
    if (set(value) != {'schema', 'candidate_sources', 'inherited_pins', 'policy'}
            or value['schema'] != 'aura-jpeg-demand-candidate-1'
            or value['policy'] != POLICY
            or set(value['candidate_sources']) != {'entry.py', 'ui_camera_service.py'}
            or value['candidate_sources']['ui_camera_service.py'] != CAMERA_AFTER
            or not isinstance(value['inherited_pins'], dict)
            or not len(REQUIRED) <= len(value['inherited_pins']) <= 128):
        raise ValueError('Candidate manifest schema or exact policy differs')
    inherited = value['inherited_pins']
    inherited_subset(inherited, REQUIRED)
    for relative, expected in value['candidate_sources'].items():
        if not sha(expected) or digest(reader(str(root / relative))) != expected:
            raise ValueError('Candidate source SHA mismatch')
    for name, expected in inherited.items():
        target = PurePosixPath(name)
        if (not target.is_absolute() or '..' in target.parts or str(target) != name
                or not sha(expected) or digest(reader(name)) != expected):
            raise ValueError('Inherited source SHA mismatch')
    original = json.loads(reader(BASE_MANIFEST), object_pairs_hook=unique)
    inherited_subset(inherited, original.get('pins'))
    operator = json.loads(reader(OPERATOR_MANIFEST), object_pairs_hook=unique)
    inherited_subset(inherited, operator.get('files'))
    meta = json.loads(reader(OPS + '/meta.json'), object_pairs_hook=unique)
    if (str(PurePosixPath(meta['candidate_root']) / 'aura') != SOURCE_ROOT
            or meta['candidate_ui_sha256'] != CAMERA_BEFORE):
        raise ValueError('Original dependency root or camera source selection changed')
    inherited_subset(inherited, {
        str(PurePosixPath(name) if PurePosixPath(name).is_absolute()
            else PurePosixPath(meta['root']) / name): expected
        for name, expected in meta['source_pins'].items()
    })
    literals = {}
    for node in ast.parse(reader(PAN_ENTRY)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ('APP_PINS', 'SHADOW_PINS'):
                literals[name] = ast.literal_eval(node.value)
    for name, prefix in [('APP_PINS', SOURCE_ROOT), ('SHADOW_PINS', OPS + '/pan-face-edge-v5')]:
        inherited_subset(inherited, {str(PurePosixPath(prefix) / relative): expected
                                    for relative, expected in literals[name].items()})
    return value


def install_camera(root, *, reader=read_static, modules=sys.modules):
    """Load the exact candidate while retaining the original dependency root."""
    if MODULE_NAME in modules:
        raise RuntimeError('Camera module already loaded before JPEG selection')
    path = Path(root) / 'ui_camera_service.py'
    raw = reader(str(path))
    if digest(raw) != CAMERA_AFTER:
        raise ValueError('Frozen JPEG candidate source changed')
    search_path = list(sys.path)
    parent = None
    module = None
    try:
        sys.path.insert(0, SOURCE_ROOT)
        parent = importlib.import_module('board.vision')
        if hasattr(parent, 'ui_camera_service'):
            raise RuntimeError('Camera package attribute already selected')
        if Path(parent.__file__).resolve() != (Path(SOURCE_ROOT) / 'board/vision/__init__.py').resolve():
            raise RuntimeError('Original vision package path changed')
        module = types.ModuleType(MODULE_NAME)
        module.__file__ = str(path)
        module.__package__ = 'board.vision'
        modules[MODULE_NAME] = module
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        module.AURA = Path(SOURCE_ROOT)
        parent.ui_camera_service = module
        return module
    except BaseException:
        if module is not None and modules.get(MODULE_NAME) is module:
            modules.pop(MODULE_NAME)
        if parent is not None and module is not None and getattr(parent, 'ui_camera_service', None) is module:
            delattr(parent, 'ui_camera_service')
        raise
    finally:
        sys.path[:] = search_path


def launch(value, root, *, run_module=runpy, installer=install_camera):
    """Select JPEG code once at the original protected operator boundary."""
    if value['policy'] != POLICY:
        raise ValueError('Verified JPEG policy required')
    original = run_module.run_path
    selections = []

    def dispatch(name, *args, **kwargs):
        if str(name) == DISPATCH_ENTRY:
            if selections or args or kwargs != {'run_name': '__main__'}:
                raise RuntimeError('Unexpected repeated or altered operator startup')
            selections.append(installer(root))
        return original(name, *args, **kwargs)

    run_module.run_path = dispatch
    try:
        result = original(BASE_ENTRY, run_name='__main__')
        if len(selections) != 1:
            raise RuntimeError('JPEG selection did not reach original protected startup')
        return result
    finally:
        run_module.run_path = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    value = verify(root, args.manifest_sha256)
    if args.verify_only:
        print(json.dumps({'status': 'SOURCE_MANIFEST_VERIFIED_NO_OWNER_STARTED',
                          'inherited_pins': len(value['inherited_pins']), 'policy': value['policy'],
                          'database_opened': False, 'native_runner_loaded': False, 'camera_opened': False}))
        return
    sys.argv = [BASE_ENTRY]
    launch(value, root)


if __name__ == '__main__':
    main()
