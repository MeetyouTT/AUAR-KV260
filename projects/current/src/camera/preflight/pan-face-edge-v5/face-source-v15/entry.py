"""Pinned v14 lazy fixed-anchor current-pixel ingress over the protected native entry."""
import hashlib
import importlib.util
import json
import runpy
import sys
from pathlib import Path

OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
F = OPS/'pan-face-edge-v5'
ROOT = F/'face-source-v15'
manifest = json.loads((ROOT/'deployment-manifest.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in manifest['pins'].items())
meta = json.loads((OPS/'meta.json').read_text())
sys.path.insert(0, str(Path(meta['candidate_root'])/'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load('face_lock_v14', ROOT/'face_lock.py').install()
load('face_timing_v14', ROOT/'face_timing.py').install()
load('stage_timing_v15', ROOT/'stage_timing.py').install()
load('face_flow', ROOT/'face_flow.py')
source = load('face_source', F/'face_source.py')
source.observation = load('face_observation_v14', ROOT/'face_observation.py').observation
load('raw_capture_v14', ROOT/'raw_capture.py').install(source)
entry = F/'native-operator-v1/native_entry_operator.py'
sys.argv = [str(entry)]
runpy.run_path(str(entry), run_name='__main__')
