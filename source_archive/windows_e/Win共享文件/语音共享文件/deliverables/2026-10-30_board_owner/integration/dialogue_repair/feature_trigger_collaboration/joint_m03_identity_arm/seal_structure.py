"""Seal the tested structure without changing any frozen product/test/worker bytes."""
from pathlib import Path
import hashlib
import json

D=Path(__file__).resolve().parent;H=D.parent;S=D/'stage_v19'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
manifest=json.loads((S/'STAGING_MANIFEST.json').read_bytes())
for relative,row in manifest['files'].items():
    assert sha(S/relative)==row['sha256'] and (S/relative).stat().st_size==row['bytes'],relative
assert len(manifest['files'])==17
r=json.loads((S/'LOCAL_REPLAY_01.json').read_bytes())
assert (r['status'],r['tests'],r['failures'],r['errors'])==('PASS',67,0,0)
assert r['temporary_stores_removed'] and r['new_threads_remaining']==0 and not r['imported_optional_packages']
assert r['identity_adapter']['counts']==dict(identity=47,independent=12)
assert r['identity_adapter']['test_bodies_and_assertions_AST_unchanged']
assert r['verification']['hashed_components']==343 and not r['verification']['live_all379_checked']
assert len(r['loaded_modules'])==8
n=json.loads((S/'STALE_INPUT_REJECTIONS.json').read_bytes())
assert n['status']=='PASS' and n['tests']==5 and not n['application_packages_imported']
manifest.update(status='STRUCTURE_FROZEN_LOCAL_67_PASS_FINAL_RETRY_SOURCE_PINS_PENDING',
    local_replay=dict(path='LOCAL_REPLAY_01.json',sha256=sha(S/'LOCAL_REPLAY_01.json'),tests=67),
    stale_inputs=dict(path='STALE_INPUT_REJECTIONS.json',sha256=sha(S/'STALE_INPUT_REJECTIONS.json'),tests=5),
    actual_ARM_executed=False,final_evidence_retry_increment_not_included=True,
    future_stage_must_be_new_directory=True,
    proof_sha256={name:sha(S/name) for name in ('ROOT_RUN.txt','WORKER_REVIEW.diff')})
dump(S/'STAGING_MANIFEST.json',manifest)
handoff=dict(schema='aura.joint-m03-identity.arm-structure-handoff.v1',
    status=manifest['status'],stage_manifest='stage_v19/STAGING_MANIFEST.json',stage_manifest_sha256=sha(S/'STAGING_MANIFEST.json'),
    worker_sha256=sha(S/'arm_public_worker.py'),candidate_manifest_sha256=sha(S/'SOURCE_MANIFEST.json'),
    runtime_artifact_count=17,product_sources=5,local_cases_passed=67,stale_rejections=5,
    actual_ARM_executed=False,final_retry_sources_pending=True,
    source_mapping_sha256=sha(S/'source_mapping.v19.json'),applied_spec_sha256=sha(S/'applied_spec.v19.json'),
    respects_root_saved_PAUSED=True,physical_or_model_or_real_private_store_access=False,
    source_identity_base_manifest_sha256=sha(H/'identity_cooperation_v90/SOURCE_MANIFEST.json'),
    root_review_of_identity_base_sha256='9911b8cedb32a15881f75907fe457733c32e135629dc7cb7ab4342661b9bb73c',
    CLI='stage_v19/ROOT_RUN.txt',worker_diff='stage_v19/WORKER_REVIEW.diff',
    stdlib_adapter='stage_v19/identity_stdlib_cases.py',
    tools={name:sha(D/name) for name in ('build_stage.py','run_local.py','check_stage_rejections.py','identity_stdlib_cases.py')})
dump(D/'HANDOFF.json',handoff)
p=H/'LATEST_FEATURE_HANDOFF.json';latest=json.loads(p.read_bytes())
latest['status']=handoff['status']
latest['latest_joint_ARM_structure']=dict(handoff='joint_m03_identity_arm/HANDOFF.json',handoff_sha256=sha(D/'HANDOFF.json'),
    status=handoff['status'],actual_ARM_executed=False,final_retry_sources_pending=True)
dump(p,latest)
print(json.dumps(dict(status=handoff['status'],handoff_sha256=sha(D/'HANDOFF.json'),stage_manifest_sha256=sha(S/'STAGING_MANIFEST.json'))))
