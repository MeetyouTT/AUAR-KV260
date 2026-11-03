"""Pinned measured-face extension over the existing protected native entry."""
import hashlib,importlib.util,json,runpy,sys
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=OPS/'pan-face-edge-v5';ROOT=F/'face-source-v6'
manifest=json.loads((ROOT/'deployment-manifest.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in manifest['pins'].items())
meta=json.loads((OPS/'meta.json').read_text());sys.path.insert(0,str(Path(meta['candidate_root'])/'aura'))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
load('face_flow',ROOT/'face_flow.py')
source=load('face_source',F/'face_source.py');original=source.observation
def measured(state):
 value=original(state)
 if value.get('state')=='READY':value['measurement_method']='current_face_features_lk_fb_or_template_v6'
 return value
source.observation=measured
entry=F/'native-operator-v1/native_entry_operator.py';sys.argv=[str(entry)];runpy.run_path(str(entry),run_name='__main__')
