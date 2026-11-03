"""Dry v25 retry-selection release bound to the actual sealed v24 release."""
import ast
import base64
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PREVIOUS = REPAIR / 'release_v24_memory_followup_candidate'
EVIDENCE = PREVIOUS / 'memory_followup_evidence'
CANONICAL = REPAIR.parent / 'production_business_acceptance'
BASE_SPEC_SHA = '9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1'
BASE_READY_SHA = 'a2f7deeb9da617fd3b602e8c6f7c48c746f786ce9ea0d1d16a206939f8ddd046'
BASE_INSTALLED_SHA = '7191e13c52f86d82ee2b8bb906b236d277a2f90ad171d8568cf9a5d5f04aa919'
BASE_MAPPING_SHA = '6fb9899571078207b7460ae71d6da52ccd211c150b7d39f54f4003e672ec21c9'
BASE_STARTUP_SHA = '888faff24fef9d85ad75bbe19bc34d63956820ccd3e6dd3f674cfe4525ed0863'
BASE_MANIFEST_SHA = '6d9b0ee5c311288e07335841c3c9e42278e8564f8be860f68412f7c2c537d8a2'
BASE_CONFIG_SHA = 'e0762cbfb88fd77238b5b1b3562fd00005bc505395867e96cfc8b1b6651fb135'
CAMERA_SPEC_SHA = 'ecdc034bd06cdd15bffe004a3ac1be3a6bc350dc3c879d91d3a19403f5c0f74a'
V24_COMMON_SHA = '6a7b340336df0786bcbf6d258704f4ad8dd112c184e8358a0ba6e654a5c2a1eb'
V24_SEAL_SHA = '3aab69f0d05193d6acc2f62e40270f4e56c8f0fae35fce39d6522ae4031a75f9'
SUMMARY_SPEC_SHA = '8376770e832d82add3ae207da3228c46c34ada89b95830cdd7536f8291224ec2'
OLD_SOURCE_PINS = {
    'common/board_memory.py': '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905',
    'common/board_memory_backoff.py': '9710c079fc589eae8f2eb26fba7f0dd80038b66736b3e45e000a98904716ce82',
}
POLICY_SHA = 'd6e459f913a6c3d9827e0d90322cb9a2fb17ada87144b853dfdf02ed300f36c6'
REVISION = 'memory-retry-selection-v25'
REVISION_KEY = 'summary_retry'
SOURCE_PATHS = tuple(sorted(OLD_SOURCE_PINS))
PAYLOAD_FINALIZED = False
APPROVED_PAYLOAD_SHA = None


def load_pinned_module(name, path, expected):
    import hashlib
    if path.is_symlink() or path.resolve() != path or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('frozen_previous_tool_changed')
    definition = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(module)
    return module


v24 = load_pinned_module('_v24_for_memory_followup', PREVIOUS / 'followup_common.py', V24_COMMON_SHA)
sha, encoded, need, pinned = v24.sha, v24.encoded, v24.need, v24.pinned
valid_sha, write_new_json = v24.valid_sha, v24.write_new_json
startup_for = v24.startup_for


def previous_seal():
    saved = sys.modules.get('followup_common')
    sys.modules['followup_common'] = v24
    try:
        return load_pinned_module('_v24_seal_for_followup', PREVIOUS / 'seal_followup.py', V24_SEAL_SHA)
    finally:
        if saved is None:
            sys.modules.pop('followup_common', None)
        else:
            sys.modules['followup_common'] = saved


def baseline():
    spec = json.loads(pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA))
    ready = json.loads(pinned(EVIDENCE / 'ready.json', BASE_READY_SHA))
    installed = json.loads(pinned(EVIDENCE / 'installed.json', BASE_INSTALLED_SHA))
    mapping = json.loads(pinned(EVIDENCE / 'source_mapping.json', BASE_MAPPING_SHA))
    previous_seal().validate_mapping(mapping, spec, ready, installed)
    marker = json.loads((EVIDENCE / 'canonical_update_state.json').read_bytes())
    need(marker == {'phase': 'COMMITTED', 'spec_sha256': BASE_SPEC_SHA, 'ready_sha256': BASE_READY_SHA},
         'actual_committed_v24_baseline_required')
    need(spec['startup_sha256'] == BASE_STARTUP_SHA and spec['source_manifest_sha256'] == BASE_MANIFEST_SHA
         and spec['configuration_sha256'] == BASE_CONFIG_SHA and spec['component_pins'] == 380
         and all(spec['component_sha256'][relative] == pin for relative, pin in OLD_SOURCE_PINS.items())
         and spec['component_sha256']['board/runtime/board_memory_policy.py'] == POLICY_SHA
         and spec['expected_final_listening_enabled'] is False, 'exact_v24_paused_source_baseline_required')
    return spec


def require_current_baseline():
    baseline()
    need((CANONICAL / 'spec.json').read_bytes() == pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA)
         and (CANONICAL / 'actual_ready.json').read_bytes() == pinned(EVIDENCE / 'ready.json', BASE_READY_SHA),
         'current_canonical_must_still_be_v24_before_preparation')


def original_source(relative):
    need(relative in OLD_SOURCE_PINS, 'only_two_retry_sources_allowed')
    if relative == 'common/board_memory.py':
        path = baseline()['summary_revision']['payload']['sources'][relative]['local_source']
    else:
        path = REPAIR / 'memory_health_collaboration/v14_validation_candidate/after/common/board_memory_backoff.py'
    return pinned(path, OLD_SOURCE_PINS[relative])


def protected_source_ast(relative, raw):
    need(relative in OLD_SOURCE_PINS, 'only_two_retry_sources_allowed')
    # Draft remains fully AST-strict until the exact retry methods are reviewed.
    return ast.dump(ast.parse(raw, feature_version=(3, 9)), include_attributes=False)


def approved_payload():
    need(APPROVED_PAYLOAD_SHA is not None, 'actual_diagnosis_and_root_two_source_selection_pending')
    selected = json.loads(pinned(HERE / 'APPROVED_PAYLOAD.json', APPROVED_PAYLOAD_SHA))
    need(set(selected) == {'baseline_spec_sha256', 'sources', 'decision'}
         and selected['baseline_spec_sha256'] == BASE_SPEC_SHA
         and set(selected['sources']) == set(SOURCE_PATHS), 'only_two_retry_sources_allowed')
    decision = selected['decision']
    need(set(decision) == {'path', 'sha256'}, 'pinned_root_source_decision_required')
    decision_value = json.loads(pinned(decision['path'], decision['sha256']))
    need(decision_value.get('reviewer') == 'root_assistant'
         and decision_value.get('selected_sources') == selected['sources'], 'root_decision_must_match_exact_source')
    boundary = decision_value.get('bounded_change', {})
    need(boundary.get('product_sources') == 2 and boundary.get('other_components') == 378
         and boundary.get('schema_permissions_commit_cleanup_and_deadline_ast_preserved') is True
         and boundary.get('validator_and_prompt_unchanged') is True,
         'reviewed_two_source_retry_behavior_required')
    for relative, row in selected['sources'].items():
        need(set(row) == {'before_sha256', 'sha256', 'local_source'}
             and row['before_sha256'] == OLD_SOURCE_PINS[relative]
             and valid_sha(row['sha256']) and row['sha256'] != row['before_sha256'], 'selected_source_before_after_required')
        raw = pinned(row['local_source'], row['sha256'])
        need(0 < len(raw) < 2097152, 'bounded_single_source_required')
        need(protected_source_ast(relative, raw) == protected_source_ast(relative, original_source(relative)),
             'exact_reviewed_retry_ast_boundary_required')
    return selected


def proposed():
    selected = approved_payload()
    spec = baseline()
    for relative, row in selected['sources'].items():
        spec['component_sha256'][relative] = row['sha256']
        spec['release_sources'][relative] = row['sha256']
    spec['startup_sha256'] = sha(encoded(startup_for(spec)))
    spec['source_manifest_sha256'] = '0' * 64
    payload_sha = sha(encoded({relative: row['sha256'] for relative, row in selected['sources'].items()}))
    stage = v24.v23.v22.CONTROL + '/' + REVISION + '-' + payload_sha[:16]
    spec[REVISION_KEY] = {'state': 'PROPOSED', 'name': REVISION, 'stage': stage,
        'payload': selected, 'previous_spec_sha256': BASE_SPEC_SHA}
    return json.loads(encoded(spec))


def validate_spec(spec, *, allow_baseline=False, allow_proposed=False):
    if REVISION_KEY not in spec:
        need(allow_baseline and spec == baseline(), 'exact_actual_v24_baseline_required')
        return spec
    expected = proposed()
    if spec[REVISION_KEY]['state'] == 'APPLIED':
        need(valid_sha(spec['source_manifest_sha256']) and spec['source_manifest_sha256'] != '0' * 64,
             'actual_followup_manifest_required')
        expected[REVISION_KEY]['state'] = 'APPLIED'
        expected['source_manifest_sha256'] = spec['source_manifest_sha256']
    else:
        need(allow_proposed and spec[REVISION_KEY]['state'] == 'PROPOSED', 'applied_followup_revision_required')
    need(spec == expected, 'only_exact_selected_single_source_followup_allowed')
    return spec


def replace_once(source, old, new):
    need(source.count(old) == 1, 'unique_reviewed_transform_anchor_required')
    return source.replace(old, new)


def publisher_remote(spec):
    validate_spec(spec, allow_baseline=True, allow_proposed=True)
    remote = v24.publisher_remote(baseline())
    if REVISION_KEY not in spec:
        return remote
    remote = v24.v23.v22.replace_node(remote, 'EXPECTED_STARTUP', 'EXPECTED_STARTUP=' + repr(startup_for(spec)))
    old = "  need(followup_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_followup_spec_changed')"
    new = "  need(followup_tx.get('applied_spec_sha256')==" + repr(BASE_SPEC_SHA) + ",'completed_followup_spec_changed')\n"
    new += """  retry_j=rebind_j.get('summary_retry',{})
  need(retry_j.get('state')=='APPLIED' and retry_j.get('stage')==SPEC['summary_retry']['stage']
       and retry_j.get('payload_sha256')==c.sha(c.encoded({rel:row['sha256'] for rel,row in SPEC['summary_retry']['payload']['sources'].items()})), 'completed_retry_source_required')
  retry_tx=c.parse(c.read(Path(SPEC['summary_retry']['stage'])/'transaction.json',retry_j['transaction_sha256']))
  need(retry_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_retry_spec_changed')"""
    remote = replace_once(remote, old, new)
    ast.parse(remote, feature_version=(3, 9))
    return remote


def payload_for(spec):
    return {relative: dict(row, base64=base64.b64encode(pinned(row['local_source'], row['sha256'])).decode('ascii'))
        for relative, row in spec[REVISION_KEY]['payload']['sources'].items()}


def execute_remote(remote, values, *, timeout=225):
    need(PAYLOAD_FINALIZED is True and APPROVED_PAYLOAD_SHA is not None, 'final_root_selected_v25_payload_required')
    approved_payload()
    current = (CANONICAL / 'spec.json').read_bytes()
    need(current in (pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA), encoded(values['SPEC'])),
         'unrelated_canonical_release_present')
    sys.path.insert(0, str(REPAIR / 'release_v18_candidate'))
    from v18_common import publisher_script, ssh_json
    return ssh_json(publisher_script(remote, values), timeout=timeout)
