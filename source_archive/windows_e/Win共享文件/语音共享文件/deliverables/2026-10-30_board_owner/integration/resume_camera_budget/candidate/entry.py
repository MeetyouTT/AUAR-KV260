"""Independently pinned entry over the unchanged protected r17 camera startup.

Run --verify-only for static file verification without importing any model,
camera/native runner or original entry. Starting this entry requires the
parent's coordinated single-publisher lifecycle transaction.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import sys

OPS = PurePosixPath('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
BASE_ENTRY = str(OPS/'pan-face-edge-v5/face-source-v17/entry.py')
BASE_MANIFEST = str(OPS/'pan-face-edge-v5/face-source-v17/deployment-manifest.json')
DISPATCH_ENTRY = str(OPS/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py')
SOURCE = str(OPS/'pan-face-edge-v5/face_source.py')
BASE_SHA = 'f26be22cb640bf44a1bd81b66bb3fa014f5b847b13320781836bf3f173387623'
BASE_MANIFEST_SHA = '84d7359f18a5a98aa5dabba967c4ededf5e35d0c43153166fc6998729a30219c'
SOURCE_SHA = '7cd8e3db7cdaa999e44df9ef2de5ff4b3870b95b2c306d3b6f9c458910c001ee'
DISPATCH_SHA = '0576a388e2c17174b4102665602aa42fbf078a3f016bdfb641c269571ce13943'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate candidate manifest key')
        result[key] = value
    return result


def read_static(name):
    target = Path(name)
    if target.is_symlink() or target.resolve() != target or not target.is_file():
        raise ValueError('Candidate source path redirected or unavailable')
    return target.read_bytes()


def verify(root, expected_manifest_sha256, *, reader=read_static):
    root = Path(root).resolve()
    if not sha(expected_manifest_sha256):
        raise ValueError('Explicit candidate manifest SHA required')
    raw = reader(str(root/'candidate-manifest.json'))
    if len(raw) > 262144 or digest(raw) != expected_manifest_sha256:
        raise ValueError('Candidate manifest SHA mismatch')
    value = json.loads(raw, object_pairs_hook=unique)
    if (set(value) != {'schema', 'candidate_sources', 'inherited_pins', 'policy'}
            or value['schema'] != 'aura-face-cadence-candidate-1'
            or value['policy'] != {'inherited_period_ms': 100, 'target_period_ms': 200,
                                   'optical_flow': True}
            or set(value['candidate_sources']) != {'entry.py', 'face_budget.py'}
            or not isinstance(value['inherited_pins'], dict)
            or not 11 <= len(value['inherited_pins']) <= 128):
        raise ValueError('Candidate manifest schema or exact policy differs')
    inherited = value['inherited_pins']
    required = {BASE_ENTRY: BASE_SHA, BASE_MANIFEST: BASE_MANIFEST_SHA,
                SOURCE: SOURCE_SHA, DISPATCH_ENTRY: DISPATCH_SHA}
    if any(inherited.get(name) != expected for name, expected in required.items()):
        raise ValueError('Protected r17 predecessor pins differ')
    for relative, expected in value['candidate_sources'].items():
        if not sha(expected) or digest(reader(str(root/relative))) != expected:
            raise ValueError('Candidate source SHA mismatch: '+relative)
    for name, expected in inherited.items():
        target = PurePosixPath(name)
        if (not target.is_absolute() or '..' in target.parts or str(target) != name
                or not sha(expected) or digest(reader(name)) != expected):
            raise ValueError('Inherited source/artifact SHA mismatch: '+name)
    original = json.loads(reader(BASE_MANIFEST), object_pairs_hook=unique)
    if (not isinstance(original.get('pins'), dict)
            or any(inherited.get(name) != expected for name, expected in original['pins'].items())):
        raise ValueError('Original r17 pin set was not preserved')
    return value


def launch(value, root, *, run_module=runpy, modules=sys.modules, policy=None):
    """Insert only at r17's existing native-operator startup call boundary."""
    if policy is None:
        spec = importlib.util.spec_from_file_location('_aura_face_budget_candidate',
                                                       str(Path(root)/'face_budget.py'))
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
    original = run_module.run_path
    calls = [0]

    def dispatch(name, *args, **kwargs):
        if str(name) == DISPATCH_ENTRY:
            if calls[0] or kwargs.get('run_name') != '__main__':
                raise RuntimeError('Unexpected repeated native-operator startup')
            source = modules.get('face_source')
            if source is None or str(source.__file__) != SOURCE:
                raise RuntimeError('Original r17 face source module not loaded')
            calls[0] += 1
            policy.install(source)
        return original(name, *args, **kwargs)

    run_module.run_path = dispatch
    try:
        result = original(BASE_ENTRY, run_name='__main__')
        source = modules.get('face_source')
        state = getattr(source, '_face_budget_candidate', {})
        if calls[0] != 1 or not state.get('installed'):
            raise RuntimeError('Face budget selection did not reach original camera startup')
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
                          'inherited_pins': len(value['inherited_pins']),
                          'policy': value['policy'], 'database_opened': False,
                          'native_runner_loaded': False, 'camera_opened': False}))
        return
    sys.argv = [BASE_ENTRY]
    launch(value, root)


if __name__ == '__main__':
    main()
