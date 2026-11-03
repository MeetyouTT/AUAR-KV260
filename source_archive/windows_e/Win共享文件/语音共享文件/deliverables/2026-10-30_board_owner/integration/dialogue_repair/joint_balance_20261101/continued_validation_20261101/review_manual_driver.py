"""Local frozen-source review for the existing manual UI test path."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[5]
RET = PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/summary_retention_acceptance_20261101'
manifest_path = RET/'manual_driver/FROZEN_MANIFEST.json'
raw = manifest_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'd3cb2a2d660d6466370bdb9ffb4ce1c813ed9afd98ca70847e8186b49a730196'
manifest = json.loads(raw)
for row in manifest['files']:
    path = Path(row['path']).resolve()
    assert path.is_relative_to(PROJECT)
    data = path.read_bytes()
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
control = (RET/'remote/manual_one_turn_control.py').read_bytes()
tree = ast.parse(control.decode('utf-8'), feature_version=(3, 9))
calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id=='ui_command']
assert len(calls)==2
actions = []
for call in calls:
    value = call.args[0]
    assert isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id=='dict'
    fields = {k.arg: ast.literal_eval(k.value) for k in value.keywords}
    assert fields['type']=='service_action' and set(fields)=={'type', 'action'}
    actions.append(fields['action'])
assert sorted(actions)==['record_start', 'record_stop']
tests = json.loads((RET/'evidence/manual_entry_public_tests.json').read_bytes())
assert tests['tests']==13 and tests['passed'] is True
assert tests['control_sha256']==hashlib.sha256(control).hexdigest()
review = dict(schema='aura-root-manual-same-scope-driver-review-1',
    decision='APPROVED_AFTER_COMPACTION_AND_USER_READINESS_ONLY',
    frozen_manifest_sha256=hashlib.sha256(raw).hexdigest(),
    combined_remote_sha256=manifest['combined_remote_sha256'],
    control_sha256=hashlib.sha256(control).hexdigest(), public_tests_passed=13,
    seed_request_hash='8db2358adf1cd749e621baaee14ec65a8b87ba50a042b8419a8dfa32c1e86f34',
    required_seed_scope_token='4c1f3c8f5a6bcad0f6e8e3f4e2ba0b60b45424e3a7d0ee4c90b8f9c98896b81b',
    allowed_existing_ui_commands=actions, maximum_manual_capture_seconds=20,
    conditions=['Fresh same owners/source/output guard; handsfree and automatic conversation remain off.',
      'Target probe proves natural age eligibility, valid directly linked summary and zero bodies in same scope.',
      'User is at device before opening the bounded manual capture.',
      'Local UI route and actual local RECORDING must be confirmed; never remote audio service.',
      'Stop only after user finishes; if capture already ended, do not send duplicate stop.',
      'No continue/toggle/select_conversation/Store or cancel command; wait for natural completion.',
      'Verify answer and seed scope equality afterwards; mismatch is not a pass.'],
    monitor_owned_directly_observed=False, selection_or_profile_grants_changed=False,
    device_access_or_models_started_by_reviewer=False)
(HERE/'ROOT_MANUAL_DRIVER_REVIEW.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(review,ensure_ascii=False))
