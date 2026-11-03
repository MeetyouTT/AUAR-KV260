"""Freeze matched C++/Python source only, with verification provenance."""
import ast
import difflib
import hashlib
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
business=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'business-integration'
native=root/'schedule-integration'
manifest=json.loads((business/'candidate-manifest.json').read_text())
checks=json.loads((native/'checks-result.json').read_text())
roundtrip=json.loads((root/'v2-roundtrip/result.json').read_text())
link=json.loads((root/'v2-target-link-result.json').read_text())['report']
assert checks['passed'] and roundtrip['passed'] and link['passed']
files={}
for name,pin in manifest['files'].items():
    raw=(business/'candidate/aura'/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pin
    ast.parse(raw,filename=name)
    files['aura/'+name]=raw
for name in ('native_bridge.cpp','native_bridge.h','native_lease_v2.hpp','native_recovery.hpp','tensor_layout.hpp'):
    raw=(native/name).read_bytes()
    pin=hashlib.sha256(raw).hexdigest()
    assert pin==checks['source_sha256'][name]==link['source_sha256'][name]
    files['native/'+name]=raw
for path,pin in roundtrip['source_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin
pins={n:hashlib.sha256(raw).hexdigest() for n,raw in sorted(files.items())}
encoded=json.dumps(pins,sort_keys=True,separators=(',',':')).encode()
identity=hashlib.sha256(encoded).hexdigest()
destination=root/'integrated'/('native-v2-'+identity[:16])
destination.mkdir(parents=True,exist_ok=False)
for name,raw in files.items():
    target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as output:output.write(raw)
source_manifest={'schema':'aura-native-python-source-2','files':manifest['files']}
(destination/'camera-python-manifest.json').write_text(json.dumps(source_manifest,indent=2,sort_keys=True)+'\n')
baseline=root/'coherent-baseline/aura'
diff=[]
for name in sorted(set(manifest['changed'])|set(manifest['new'])):
    previous=baseline/name
    before=previous.read_text().splitlines(keepends=True) if previous.exists() else []
    after=(destination/'aura'/name).read_text().splitlines(keepends=True)
    diff.extend(difflib.unified_diff(before,after,fromfile='baseline/aura/'+name,
                                    tofile='candidate/aura/'+name))
(destination/'camera-source.patch').write_text(''.join(diff))
report={'schema':'aura-native-source-candidate-2','candidate_id':'native-v2-'+identity[:16],
    'source_set_sha256':identity,'status':'SOURCE_INTEGRATED_NOT_DEPLOYED',
    'files_sha256':pins,'python_files':len(manifest['files']),
    'changed_python':manifest['changed'],'new_python':manifest['new'],
    'native_files':5,'target_library_sha256':link['library_sha256'],
    'target_object_sha256':link['object_sha256'],
    'verification':{'native_checks_sha256':hashlib.sha256((native/'checks-result.json').read_bytes()).hexdigest(),
        'actual_cdll_checks_sha256':hashlib.sha256((root/'v2-roundtrip/result.json').read_bytes()).hexdigest(),
        'target_link_checks_sha256':hashlib.sha256((root/'v2-target-link-result.json').read_bytes()).hexdigest()},
    'real_model_inferences':0,'target_model_factories_called':0,
    'target_library_constant_abi_checked':(root/'v2-target-constant-abi-result.json').exists(),
    'limitations':['Same-boot legacy process has no final sealed checkpoint; current protection cannot be silently unlocked',
                   'Actual INT8 output equivalence, runtime throughput and long stability remain unverified']}
(destination/'candidate.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(root/'latest-integrated.json').write_text(json.dumps({'path':str(destination),**report},indent=2)+'\n')
print(json.dumps({'path':str(destination),'python_files':len(manifest['files']),
                  'candidate_id':report['candidate_id'],'native_files':5,'real_model_inferences':0}))
