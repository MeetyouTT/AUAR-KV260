"""Seal the final 19-artifact/92-case public stage, preserving all frozen sources."""
from pathlib import Path
import hashlib
import json

D=Path(__file__).resolve().parent;H=D.parent;REPAIR=H.parent
S=D/'stage_v19_final_06e5';F=H/'joint_m03_identity_arm/stage_v19'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
m=json.loads((S/'STAGING_MANIFEST.json').read_bytes())
assert len(m['files'])==19 and m['source_files']==6 and m['case_count']==92
for rel,row in m['files'].items():
    assert sha(S/rel)==row['sha256'] and (S/rel).stat().st_size==row['bytes'],rel
assert sha(S/'arm_public_worker.py')=='10ae4c0f696d4ae332ff8c09c19c6a4668494d809ae09a1643e6fe86b74f52b2'
assert sha(S/'SOURCE_MANIFEST.json')=='7ad9bb44686f86068ff61e89865eb0333785287ca1949bbdcc4cfe138bd1ef4f'
r=json.loads((S/'LOCAL_REPLAY_01.json').read_bytes())
assert (r['status'],r['tests'],r['failures'],r['errors'])==('PASS',92,0,0)
assert r['temporary_stores_removed'] and r['new_threads_remaining']==0 and not r['imported_optional_packages']
assert r['identity_adapter']['counts']==dict(identity=47,independent=12)
assert r['memory_regression']['cases']==25 and r['memory_regression']['proof']['original_class_method_assertion_AST_unchanged']
assert r['memory_regression']['proof']['AFTER_modules_are_current_six_source_runtime']
assert r['verification']['hashed_components']==343 and not r['verification']['live_all379_checked']
sources=json.loads((S/'SOURCE_MANIFEST.json').read_bytes())
for name,rel in [('common.board_memory','common/board_memory.py'),('board.runtime.board_business','board/runtime/board_business.py'),
    ('board.runtime.board_speaker_business','board/runtime/board_speaker_business.py'),
    ('board.runtime.history_delete','board/runtime/history_delete.py'),('tools.provisional_voice','tools/provisional_voice.py'),
    ('tools.production_memory_presentation','tools/production_memory_presentation.py')]:
    assert r['loaded_modules'][name]['sha256']==sources['files'][rel]['sha256']
assert sha(F/'STAGING_MANIFEST.json')=='9b3798a185c2e731c764019759bafbe1430acef88f8606f81eff55026e9da063'
fm=json.loads((F/'STAGING_MANIFEST.json').read_bytes())
assert all(sha(F/rel)==row['sha256'] for rel,row in fm['files'].items())
review=REPAIR/'review_voice_visual_guard/REVIEW.json'
assert sha(review)=='c2ac21973bb4efec63dcf30b80219c74439dde9f57c44436373bab9dc88a9d3c'
combined=REPAIR/'voice_visual_timeline_review_v90/COMBINED_SIX_SOURCE_MANIFEST.json'
assert sha(combined)=='06e5ced57c55b0ef551424c37b08c1a9bd5f43217af98c8a6f9170c1cc597f91'
dump(S/'UPLOAD_LIST.json',[dict(relative_path=rel,source=str(S/rel),sha256=row['sha256'],bytes=row['bytes']) for rel,row in m['files'].items()])
argv=['python3','-B','{S}/arm_public_worker.py','--runtime-root','{R}/runtime/aura','--startup-config','{R}/startup/config.json',
    '--candidate-root','{S}/after','--mapping','{S}/source_mapping.v19.json','--candidate-manifest','{S}/SOURCE_MANIFEST.json',
    '--candidate-manifest-sha256',sha(S/'SOURCE_MANIFEST.json'),
    '--original-review','{S}/tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py',
    '--independent-tests','{S}/test_independent_boundaries.py','--public-worker','{S}/public_worker.py',
    '--applied-spec','{S}/applied_spec.v19.json','--identity-tests','{S}/identity_tests.py',
    '--identity-independent','{S}/identity_independent.py','--speaker-fixtures','{S}/speaker_fixtures.py',
    '--face-fixtures','{S}/face_fixtures.py','--identity-adapter','{S}/identity_stdlib_cases.py',
    '--memory-regression','{S}/memory_public_regressions.py','--root-coordinated-slot','{ROOT_SLOT}','--output','{OUT}']
dump(S/'ROOT_ARM_CLI.json',dict(argv=argv,production_root='/home/root/aura-board-business-20261030/production-5259eab11e42af13',
    recommended_new_stage='/home/root/aura-public-feature-validation-20261031/joint-final-06e5-92',
    preserve_saved_false_PAUSED=True,root_fresh_owner_and_idle_check_required=True))
proofs={name:sha(S/name) for name in ('LOCAL_REPLAY_01.json','ROOT_RUN.txt','UPLOAD_LIST.json','ROOT_ARM_CLI.json','WORKER_REVIEW.diff')}
m.update(status='READY_FOR_ROOT_PUBLIC_ARM_92_LOCAL_PASS_NOT_DEPLOYED',local_tests=92,
    actual_ARM_executed=False,source_composition_sha256=sha(combined),memory_independent_review_sha256=sha(review),
    memory_adapter_proof_sha256=sha(D/'MEMORY_ADAPTER_PROOF.json'),proof_sha256=proofs,
    original67_retained=True,memory25_original_class_method_assertion_AST_unchanged=True,
    before_controls_are_explicit_embedded_source_fixtures_not_runtime_fallbacks=True,
    unmapped_legacy_modules_not_loaded=['test_board_memory_review.py','test_board_memory_completion.py'])
dump(S/'STAGING_MANIFEST.json',m)
handoff=dict(schema='aura.joint-six-source.final-arm-handoff.v1',status=m['status'],
    stage='stage_v19_final_06e5',stage_manifest_sha256=sha(S/'STAGING_MANIFEST.json'),
    worker_sha256=sha(S/'arm_public_worker.py'),candidate_manifest_sha256=sha(S/'SOURCE_MANIFEST.json'),
    upload_list='stage_v19_final_06e5/UPLOAD_LIST.json',upload_list_sha256=sha(S/'UPLOAD_LIST.json'),
    CLI='stage_v19_final_06e5/ROOT_RUN.txt',structured_CLI='stage_v19_final_06e5/ROOT_ARM_CLI.json',
    runtime_artifacts=19,product_sources=6,baseline_components=379,proposed_components=380,
    local_tests=92,core_tests=67,memory_tests=25,temporary_stores_removed=True,new_threads_remaining=0,
    imported_optional_packages=[],actual_ARM_executed=False,deployed=False,
    root_review_memory_sha256=sha(review),root_review_identity_sha256='9911b8cedb32a15881f75907fe457733c32e135629dc7cb7ab4342661b9bb73c',
    composition_input_manifest_sha256=sha(combined),memory_adapter_proof_sha256=sha(D/'MEMORY_ADAPTER_PROOF.json'),
    old_stage_and_17_artifacts_unchanged=True,physical_devices_models_real_private_store_access=False,
    root_saved_false_PAUSED_unchanged=True,missing_legacy_dependency_not_filled=True)
dump(D/'FINAL_ARM_HANDOFF.json',handoff)
p=H/'LATEST_FEATURE_HANDOFF.json';latest=json.loads(p.read_bytes());latest['status']=m['status']
latest['latest_joint_final_ARM']=dict(handoff='joint_m03_identity_arm_v2/FINAL_ARM_HANDOFF.json',
    handoff_sha256=sha(D/'FINAL_ARM_HANDOFF.json'),stage_manifest_sha256=sha(S/'STAGING_MANIFEST.json'),
    local_tests=92,actual_ARM_executed=False,deployed=False)
dump(p,latest)
print(json.dumps(dict(status=m['status'],handoff_sha256=sha(D/'FINAL_ARM_HANDOFF.json'),
    stage_manifest_sha256=sha(S/'STAGING_MANIFEST.json'),upload_list_sha256=sha(S/'UPLOAD_LIST.json'))))
