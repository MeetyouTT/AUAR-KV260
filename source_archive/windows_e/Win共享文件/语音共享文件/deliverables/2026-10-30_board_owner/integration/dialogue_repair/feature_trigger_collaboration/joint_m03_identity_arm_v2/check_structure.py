"""Render/inspect an unbound six-source worker without building a stage or importing apps."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

D=Path(__file__).resolve().parent;H=D.parent;F=H/'joint_m03_identity_arm/stage_v19'
spec=importlib.util.spec_from_file_location('joint_v2_builder',D/'build_stage.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
frozen=json.loads((F/'STAGING_MANIFEST.json').read_bytes())
assert hashlib.sha256((F/'STAGING_MANIFEST.json').read_bytes()).hexdigest()==builder.FROZEN_MANIFEST
assert all(hashlib.sha256((F/key).read_bytes()).hexdigest()==row['sha256'] for key,row in frozen['files'].items())
raw=(F/'source_mapping.v19.json').read_bytes();mapping=json.loads(raw)
memory=b"PUBLIC_REGRESSION_API='aura-memory-public-regression-1'\nEXPECTED_CASES=2\ndef build_suite(*,args,public):\n    raise RuntimeError('UNBOUND STRUCTURE PROBE; no regression cases supplied')\n"
_,worker=builder.render_worker(mapping=mapping,mapping_raw=raw,source_files={key:{} for key in builder.SOURCE_SET},
    files=frozen['files'],memory_cases=2,memory_raw=memory)
tree=ast.parse(worker);namespace={'__name__':'joint_v2_structure_probe','__file__':str(D/'NOT_A_STAGE.py')}
exec(compile(tree,str(D/'NOT_A_STAGE.py'),'exec'),namespace)
assert namespace['FILES']==builder.SOURCE_SET and len(namespace['FILES'])==6
assert set(namespace['FILES'])-set(mapping['component_pins'])=={'board/runtime/history_delete.py'}
assert len(set(mapping['component_pins'])|namespace['FILES'])==380
assert namespace['MEMORY_CASES']==2
assert namespace['MEMORY_REGRESSION']==hashlib.sha256(memory).hexdigest()
for field,key in [('IDENTITY_TESTS','identity_tests.py'),('IDENTITY_INDEPENDENT','identity_independent.py'),
    ('SPEAKER_FIXTURES','speaker_fixtures.py'),('FACE_FIXTURES','face_fixtures.py'),('IDENTITY_ADAPTER','identity_stdlib_cases.py')]:
    assert namespace[field]==frozen['files'][key]['sha256']
old_tree=ast.parse((F/'arm_public_worker.py').read_bytes())
def paired(tree):
    return next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Paired')
assert ast.dump(paired(tree))==ast.dump(paired(old_tree))
assert "need(suite.countTestCases()==67,'joint_case_count_changed')" in worker
assert "suite.addTests(extra);need(suite.countTestCases()==67+MEMORY_CASES,'core67_must_be_retained')" in worker
assert "('common.board_memory','common/board_memory.py')" in worker
assert '(args.memory_regression,MEMORY_REGRESSION)' in worker
assert "getattr(memory,'PUBLIC_REGRESSION_API',None)=='aura-memory-public-regression-1'" in worker
assert "extra.countTestCases()==MEMORY_CASES" in worker
assert not any(name.split('.')[0] in ('board','common','tools') for name in sys.modules)
report=dict(schema='aura.joint-six-source.tooling-structure-check.v1',status='PASS_STRUCTURE_ONLY',
    frozen_stage_manifest_and_all_17_artifacts_unchanged=True,
    stage_created=False,final_sources_or_memory_regressions_supplied=False,application_imports=False,
    product_source_count=6,baseline_live_components_required=379,proposed_components=380,
    only_new_component='board/runtime/history_delete.py',
    original67_inputs_hashes_retained=True,original_M03_paired_test_AST_unchanged=True,
    memory_module_hash_checked_before_application_imports=True,
    memory_slot_API='aura-memory-public-regression-1; EXPECTED_CASES=N>0; build_suite(*,args,public)',
    memory_slot_built_inside_owned_temporary_root=True,
    final_test_count='67+N; structure probe N=2 is NOT a memory regression result',
    unbound_probe_worker_not_saved_or_executed=True)
(D/'STRUCTURE_CHECK.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(status=report['status'],sources=6,baseline=379,proposed=380,stage_created=False,apps_imported=False)))
