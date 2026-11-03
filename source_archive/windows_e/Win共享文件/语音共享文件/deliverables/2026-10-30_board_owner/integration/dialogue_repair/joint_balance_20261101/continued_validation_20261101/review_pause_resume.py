"""Independent local review of the explicit-continue source change."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[5]
CANDIDATE = HERE/'pause_resume_candidate'
SPEC = PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/package/subtitle_receipt/candidate_spec.json'
RELATIVE = 'tools/voice_first_recording.py'
BEFORE = '57375530fddbcf7a8f431201bf86ba904d289828e69a82cdee81ab0324987427'
AFTER = '54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'
digest = lambda data: hashlib.sha256(data).hexdigest()
spec_raw = SPEC.read_bytes()
assert digest(spec_raw)=='62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
spec = json.loads(spec_raw)
handoff_raw = (CANDIDATE/'FROZEN_HANDOFF.json').read_bytes()
handoff = json.loads(handoff_raw)
for name, pin in handoff['files'].items():
    data = (CANDIDATE/name).read_bytes()
    assert len(data)==pin['bytes'] and digest(data)==pin['sha256'], name
assert spec['component_sha256'][RELATIVE]==BEFORE
for pin in handoff['support_sources']:
    assert digest(Path(pin['path']).read_bytes())==pin['sha256']==spec['component_sha256'][pin['component']]
before, after = [(CANDIDATE/d/RELATIVE).read_bytes() for d in ('before','after')]
assert digest(before)==BEFORE and digest(after)==AFTER
def methods(data):
    tree = ast.parse(data.decode('utf-8'), feature_version=(3,9))
    cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VoiceFirstRecordingController')
    items = [n for n in cls.body if isinstance(n,ast.FunctionDef)]
    assert len({n.name for n in items})==len(items)
    return {n.name:ast.dump(n,include_attributes=False) for n in items}
old, new = methods(before), methods(after)
changed = sorted(name for name in old if old[name]!=new[name])
added = sorted(set(new)-set(old))
assert changed==sorted(['__init__','_finish_session','cancel','handsfree_toggle','_monitor_tick'])
assert added==sorted(['_conversation_resume_binding','_same_resume_binding','_select_listening_conversation'])
assert handoff['tests']['tests']==9 and handoff['tests']['passed'] is True
review = dict(schema='aura-root-explicit-continue-source-review-1',
    decision='APPROVED_SINGLE_SOURCE_FOR_PUBLIC_ARM_AND_SERIAL_PACKAGE_PREPARATION',
    requested_behavior='User explicitly chose to continue the current conversation after pause.',
    base_spec_sha256=digest(spec_raw), source=RELATIVE, before_sha256=BEFORE, after_sha256=AFTER,
    frozen_handoff_sha256=digest(handoff_raw), matched_support_sources=len(handoff['support_sources']),
    changed_methods=changed, added_helpers=added, local_public_tests=9,
    checks=['Pending RAM binding is created only by explicit UI enable for an already admitted anonymous active==saved conversation.',
      'Binding matches the same jobs, selection, boot, transport session and CID under the existing jobs RLock at consumption.',
      'Original select_conversation handles generation/session invalidation and durable reference; no direct selection-file writes added.',
      'Cancel/finish clear the one-use marker; automatic silence expiry/rebuild still selects a new anonymous conversation.',
      'Saved file alone grants no continuation; profile/custom scope providers keep the original route with no new grants.',
      'Original recording, ASR, model, playback, presentation, memory-policy and mechanical code remain unchanged.'],
    deployment_claimed=False, physical_or_long_duration_acceptance_claimed=False,
    device_model_or_private_database_access_by_reviewer=False)
(HERE/'ROOT_PAUSE_RESUME_SOURCE_REVIEW.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(review,ensure_ascii=False))
