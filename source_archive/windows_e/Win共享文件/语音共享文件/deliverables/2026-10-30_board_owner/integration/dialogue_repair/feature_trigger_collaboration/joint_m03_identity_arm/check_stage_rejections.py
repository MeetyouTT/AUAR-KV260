"""Check that stale public inputs fail before importing any application package."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS

D=Path(__file__).resolve().parent;H=D.parent;S=D/'stage_v19'
spec=importlib.util.spec_from_file_location('joint_rejection_entry',S/'arm_public_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
a=NS(runtime_root=S/'public_runtime_v19',candidate_root=S/'after',mapping=S/'source_mapping.v19.json',
    candidate_manifest=S/'SOURCE_MANIFEST.json',candidate_manifest_sha256=hashlib.sha256((S/'SOURCE_MANIFEST.json').read_bytes()).hexdigest(),
    original_review=S/'tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py',
    independent_tests=S/'test_independent_boundaries.py',public_worker=S/'public_worker.py',
    applied_spec=S/'applied_spec.v19.json',identity_tests=S/'identity_tests.py',identity_independent=S/'identity_independent.py',
    speaker_fixtures=S/'speaker_fixtures.py',face_fixtures=S/'face_fixtures.py',identity_adapter=S/'identity_stdlib_cases.py',
    output=S/'UNUSED_REJECTION_OUTPUT.json',startup_config=None,local_replay=True,root_coordinated_slot=None)
cases=[('old_v90_mapping',dict(mapping=H/'candidate_m03_v90_stage/source_mapping.v90.json'),'frozen_mapping_changed'),
    ('old_v90_runtime',dict(runtime_root=H/'candidate_m03_v90_stage/public_runtime_v90'),'baseline_component_changed:'),
    ('only_M03_three_sources',dict(candidate_root=H/'candidate_m03_v90_stage/after'),'exact_five_file_overlay_required'),
    ('wrong_candidate_manifest_sha',dict(candidate_manifest_sha256='0'*64),'candidate_manifest_changed'),
    ('wrong_identity_test_source',dict(identity_tests=H/'identity_cooperation_v90/PUBLIC_COUNTEREXAMPLES_FROZEN.py'),'joint_public_artifact_changed')]
rows=[]
for name,changes,reason in cases:
    b=copy.copy(a)
    for key,value in changes.items():setattr(b,key,value)
    try:worker.verify(b)
    except ValueError as exc:
        assert str(exc).startswith(reason),(name,str(exc))
        rows.append(dict(case=name,status='REJECTED_AS_EXPECTED',reason=str(exc)))
    else:raise AssertionError('Stale input accepted: '+name)
    assert not any(n.split('.')[0] in ('board','common','tools') for n in sys.modules)
assert not a.output.exists()
value=dict(status='PASS',tests=len(rows),application_packages_imported=False,production_or_fixture_files_changed=False,cases=rows)
(S/'STALE_INPUT_REJECTIONS.json').write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(status='PASS',stale_rejections=len(rows),app_imports=False)))
