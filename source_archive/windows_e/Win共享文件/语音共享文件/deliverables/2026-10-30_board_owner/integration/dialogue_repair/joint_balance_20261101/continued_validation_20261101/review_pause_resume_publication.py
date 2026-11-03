"""Local frozen transaction review; does not import the live publisher."""
import base64
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[5]
RET=PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/summary_retention_acceptance_20261101'
JP=RET.parent/'joint_performance_20261101'
BASE=JP/'package/subtitle_receipt'
BUNDLE=RET/'package/pause_resume'
SOURCE='tools/voice_first_recording.py'
BEFORE='57375530fddbcf7a8f431201bf86ba904d289828e69a82cdee81ab0324987427'
AFTER='54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'
ROOT='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=lambda name:(BUNDLE/name).read_bytes()
read=lambda name:json.loads(raw(name))
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
old_bundle=(BASE/'BUNDLE_MANIFEST.json').read_bytes()
assert sha(old_bundle)=='0a66025ca8d28c8c30f9fd8b99b36d70e1d87d0b3c52648200636c223bcd88ba'
for name,pin in json.loads(old_bundle)['files'].items():assert sha((BASE/name).read_bytes())==pin,name
bundle_raw=raw('BUNDLE_MANIFEST.json')
for name,pin in json.loads(bundle_raw)['files'].items():assert sha(raw(name))==pin,name
assert sha(raw('base_spec.json'))=='62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
assert sha(raw('base_startup.json'))=='22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311'
assert sha(raw('base_manifest.json'))=='5b741bff8039a4f71110b06cce88ff40bea32a27ace718a263f6879f79deaa2b'
assert sha(raw('rollback/voice_first_recording.py'))==BEFORE
assert sha(raw('payload/voice_first_recording.py'))==AFTER
assert raw('payload/voice_first_recording.py')==(HERE/'pause_resume_candidate/after'/SOURCE).read_bytes()
old,new=read('base_spec.json'),read('candidate_spec.json')
assert len(new['component_sha256'])==len(old['component_sha256'])==380
assert set(new['component_sha256'])==set(old['component_sha256'])
assert [k for k in old['component_sha256'] if old['component_sha256'][k]!=new['component_sha256'][k]]==[SOURCE]
start=read('base_startup.json');start['component_sha256'][SOURCE]=AFTER
assert read('candidate_startup.json')==start
manifest=read('base_manifest.json');revision=read('candidate_manifest.json')['pause_resume_current_conversation']
assert revision['source']==SOURCE and revision['before_sha256']==BEFORE and revision['after_sha256']==AFTER
assert revision['parent_spec_sha256']==sha(raw('base_spec.json'))
assert revision['parent_startup_sha256']==sha(raw('base_startup.json'))
assert revision['parent_manifest_sha256']==sha(raw('base_manifest.json'))
manifest['component_pins'][SOURCE]=AFTER
manifest['files']['runtime/aura/'+SOURCE]=dict(bytes=len(raw('payload/voice_first_recording.py')),sha256=AFTER)
manifest['files']['startup/config.json']=dict(bytes=len(raw('candidate_startup.json')),sha256=sha(raw('candidate_startup.json')))
manifest['pause_resume_current_conversation']=revision
assert read('candidate_manifest.json')==manifest
expected=copy.deepcopy(old)
expected['component_sha256'][SOURCE]=AFTER;expected['release_sources'][SOURCE]=AFTER
expected.update(startup_sha256=sha(raw('candidate_startup.json')),source_manifest_sha256=sha(raw('candidate_manifest.json')),
                pause_resume_current_conversation=dict(revision,state='APPLIED'))
assert new==expected
assert encoded(old)==raw('base_spec.json') and encoded(new)==raw('candidate_spec.json')
for name in ('gui.json','publisher_definitions.py','camera_binding_runtime.py','single_projection_overlay.py'):
    assert raw(name)==(BASE/name).read_bytes(),name
targets={
 'voice_first_recording.py':(ROOT+'/runtime/aura/'+SOURCE,raw('rollback/voice_first_recording.py'),raw('payload/voice_first_recording.py')),
 'production-source-manifest.json':(ROOT+'/production_source_manifest.json',raw('base_manifest.json'),raw('candidate_manifest.json')),
 'startup-config.json':(ROOT+'/startup/config.json',raw('base_startup.json'),raw('candidate_startup.json'))}
parents=json.loads((BASE/'forward_plan.json').read_bytes())['parent_transactions']
for direction in ('forward','rollback'):
    plan=read(direction+'_plan.json')
    assert set(plan['targets'])==set(targets) and plan['changed_source']==SOURCE
    assert plan['allow_known_mixed_on_first_apply'] is (direction=='rollback')
    for name,(path,a,b) in targets.items():
        before,after=(a,b) if direction=='forward' else (b,a)
        row=plan['targets'][name]
        assert row['path']==path and row['old_sha256']==sha(before) and row['new_sha256']==sha(after)
        assert base64.b64decode(row['new_base64'],validate=True)==after
    assert sha(encoded(plan['transaction']))==plan['transaction_sha256']
    for key,value in parents.items():assert plan['parent_transactions'][key]==value
    assert plan['parent_transactions']['subtitle_submit_receipt']['spec_sha256']==sha(raw('base_spec.json'))
runner=(JP/'tools/publish_subtitle_receipt.py').read_text(encoding='utf-8')
runner=runner.replace("root=HERE/'package/subtitle_receipt'","root=HERE/'package/pause_resume'",1)
runner=runner.replace("review['candidate_source_sha256']=='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'",
                      "review['candidate_source_sha256']=='"+AFTER+"'",1)
runner=runner.replace("('subtitle_receipt_'+a.direction","('pause_resume_'+a.direction",1)
assert (RET/'tools/publish_pause_resume.py').read_text(encoding='utf-8')==runner
prep=read('PREPARATION.json');arm_raw=Path(prep['arm_evidence']).read_bytes();arm=json.loads(arm_raw)['result']
assert sha(arm_raw)==prep['arm_evidence_sha256']==revision['arm_evidence_sha256']
assert arm['status']=='PASSED' and arm['machine']=='aarch64' and arm['public_tests']==9
assert arm['candidate_sha256']==AFTER and arm['private_database_or_device_services_used'] is False
review=dict(schema='aura-root-explicit-continue-frozen-publication-review-1',status='APPROVED_FOR_SERIAL_OPERATOR',
    bundle_manifest_sha256=sha(bundle_raw),candidate_source_sha256=AFTER,
    new_spec_sha256=sha(raw('candidate_spec.json')),new_startup_sha256=sha(raw('candidate_startup.json')),
    new_manifest_sha256=sha(raw('candidate_manifest.json')),arm_evidence_sha256=sha(arm_raw),unchanged_components=379,
    checks=['Full old/new frozen hashes; exact one-source derivation; original GUI, camera, memory, caption and 379-component bytes retained.',
      'Forward and bounded rollback target exactly source, startup and manifest; all ancestors plus subtitle parent retained.',
      'Publisher equals prior reviewed entry with three scoped substitutions; original shutdown/locks/guard chain retained.',
      'Actual aarch64 nine public tests passed; no device commands executed by root reviewer.'],
    live_resume_or_recall_accepted=False,device_model_private_data_access_by_reviewer=False)
(HERE/'SERIAL_PAUSE_RESUME_OPERATOR_REVIEW.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(review,ensure_ascii=False))
