"""Dry v24 single-source follow-up bound to the actual sealed v23 release."""
import ast
import base64
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PREVIOUS = REPAIR / 'release_v23_memory_summary_candidate'
EVIDENCE = PREVIOUS / 'memory_summary_evidence'
CANONICAL = REPAIR.parent / 'production_business_acceptance'
BASE_SPEC_SHA = '8376770e832d82add3ae207da3228c46c34ada89b95830cdd7536f8291224ec2'
BASE_READY_SHA = 'ab81bbc36ad34cbdcbc36a5830a36b2937e7975c40bd44accc7fb258c9a70aaa'
BASE_INSTALLED_SHA = '0c60f434447bf3704b326ff98a4af76d3a9eb44730db92f816a701bdd8f581ea'
BASE_MAPPING_SHA = 'b053291dd3af5f5bc6e441288b5db91521226b903958bcbf3ca939a6541945d6'
BASE_STARTUP_SHA = 'd848dc90cf9a890fb8bc66b2c494b78c2ae39a7e22a4743fe0ab917ca3edbae8'
BASE_MANIFEST_SHA = '8e4d3a90f20520c518f28fa12cbf9093f17405f4d9ed2bb9edf2ac46890d496a'
BASE_CONFIG_SHA = 'e0762cbfb88fd77238b5b1b3562fd00005bc505395867e96cfc8b1b6651fb135'
CAMERA_SPEC_SHA = 'ecdc034bd06cdd15bffe004a3ac1be3a6bc350dc3c879d91d3a19403f5c0f74a'
V23_COMMON_SHA = '7b7227447bee67e38ed4371fc4d58979bdf56f2f36c3745c8fdd934e012d6a25'
V23_SEAL_SHA = '99a5906d2412216df0a45ccd9cc9fcb122c35c1b976bf2b9d48638eb7cfb1ef2'
OLD_SOURCE_PINS = {
    'common/board_memory.py': '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905',
    'board/runtime/board_memory_policy.py': 'a862cc22f6c23ae90d17ef06614cdf90fa0eb4605ad0a8b74766d102aad404aa',
}
REVISION = 'memory-summary-followup-v24'
REVISION_KEY = 'summary_followup'
POLICY_RELATIVE = 'board/runtime/board_memory_policy.py'
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


v23 = load_pinned_module('_v23_for_memory_followup', PREVIOUS / 'summary_common.py', V23_COMMON_SHA)
sha, encoded, need, pinned = v23.sha, v23.encoded, v23.need, v23.pinned
valid_sha, write_new_json = v23.valid_sha, v23.write_new_json
startup_for = v23.startup_for


def previous_seal():
    saved = sys.modules.get('summary_common')
    sys.modules['summary_common'] = v23
    try:
        return load_pinned_module('_v23_seal_for_followup', PREVIOUS / 'seal_summary.py', V23_SEAL_SHA)
    finally:
        if saved is None:
            sys.modules.pop('summary_common', None)
        else:
            sys.modules['summary_common'] = saved


def baseline():
    spec = json.loads(pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA))
    ready = json.loads(pinned(EVIDENCE / 'ready.json', BASE_READY_SHA))
    installed = json.loads(pinned(EVIDENCE / 'installed.json', BASE_INSTALLED_SHA))
    mapping = json.loads(pinned(EVIDENCE / 'source_mapping.json', BASE_MAPPING_SHA))
    previous_seal().validate_mapping(mapping, spec, ready, installed)
    marker = json.loads((EVIDENCE / 'canonical_update_state.json').read_bytes())
    need(marker == {'phase': 'COMMITTED', 'spec_sha256': BASE_SPEC_SHA, 'ready_sha256': BASE_READY_SHA},
         'actual_committed_v23_baseline_required')
    need(spec['startup_sha256'] == BASE_STARTUP_SHA and spec['source_manifest_sha256'] == BASE_MANIFEST_SHA
         and spec['configuration_sha256'] == BASE_CONFIG_SHA and spec['component_pins'] == 380
         and all(spec['component_sha256'][relative] == pin for relative, pin in OLD_SOURCE_PINS.items())
         and spec['expected_final_listening_enabled'] is False, 'exact_v23_paused_source_baseline_required')
    return spec


def require_current_baseline():
    baseline()
    need((CANONICAL / 'spec.json').read_bytes() == pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA)
         and (CANONICAL / 'actual_ready.json').read_bytes() == pinned(EVIDENCE / 'ready.json', BASE_READY_SHA),
         'current_canonical_must_still_be_v23_before_preparation')


def original_policy():
    row = baseline()['summary_revision']['payload']['sources'][POLICY_RELATIVE]
    need(row['sha256'] == OLD_SOURCE_PINS[POLICY_RELATIVE], 'actual_v23_policy_source_required')
    return pinned(row['local_source'], OLD_SOURCE_PINS[POLICY_RELATIVE])


def protected_source_ast(raw):
    tree = ast.parse(raw, feature_version=(3, 9))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardSummaryClient']
    need(len(classes) == 1, 'one_original_summary_client_required')
    methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == '_messages']
    need(len(methods) == 1, 'one_original_messages_method_required')
    methods[0].body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def approved_payload():
    need(APPROVED_PAYLOAD_SHA is not None, 'actual_diagnosis_and_root_single_source_selection_pending')
    selected = json.loads(pinned(HERE / 'APPROVED_PAYLOAD.json', APPROVED_PAYLOAD_SHA))
    need(set(selected) == {'baseline_spec_sha256', 'sources', 'decision'}
         and selected['baseline_spec_sha256'] == BASE_SPEC_SHA
         and set(selected['sources']) == {POLICY_RELATIVE}, 'only_summary_policy_source_allowed')
    decision = selected['decision']
    need(set(decision) == {'path', 'sha256'}, 'pinned_root_source_decision_required')
    decision_value = json.loads(pinned(decision['path'], decision['sha256']))
    need(decision_value.get('reviewer') == 'root_assistant'
         and decision_value.get('selected_sources') == selected['sources'], 'root_decision_must_match_exact_source')
    boundary = decision_value.get('bounded_change', {})
    need(boundary.get('product_sources') == 1 and boundary.get('other_components') == 379
         and boundary.get('schema_permissions_commit_cleanup_and_deadline_ast_preserved') is True,
         'reviewed_single_source_protected_behavior_required')
    for relative, row in selected['sources'].items():
        need(set(row) == {'before_sha256', 'sha256', 'local_source'}
             and row['before_sha256'] == OLD_SOURCE_PINS[relative]
             and valid_sha(row['sha256']) and row['sha256'] != row['before_sha256'], 'selected_source_before_after_required')
        raw = pinned(row['local_source'], row['sha256'])
        need(0 < len(raw) < 2097152, 'bounded_single_source_required')
        need(protected_source_ast(raw) == protected_source_ast(original_policy()),
             'only_messages_body_may_change_all_other_module_ast_must_match_v23')
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
    stage = v23.v22.CONTROL + '/' + REVISION + '-' + payload_sha[:16]
    spec[REVISION_KEY] = {'state': 'PROPOSED', 'name': REVISION, 'stage': stage,
        'payload': selected, 'previous_spec_sha256': BASE_SPEC_SHA}
    return json.loads(encoded(spec))


def validate_spec(spec, *, allow_baseline=False, allow_proposed=False):
    if REVISION_KEY not in spec:
        need(allow_baseline and spec == baseline(), 'exact_actual_v23_baseline_required')
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
    remote = v23.publisher_remote(baseline())
    if REVISION_KEY not in spec:
        return remote
    remote = v23.v22.replace_node(remote, 'EXPECTED_STARTUP', 'EXPECTED_STARTUP=' + repr(startup_for(spec)))
    old = "  need(summary_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_summary_spec_changed')"
    new = "  need(summary_tx.get('applied_spec_sha256')==" + repr(BASE_SPEC_SHA) + ",'completed_summary_spec_changed')\n"
    new += """  followup_j=rebind_j.get('summary_followup',{})
  need(followup_j.get('state')=='APPLIED' and followup_j.get('stage')==SPEC['summary_followup']['stage']
       and followup_j.get('payload_sha256')==c.sha(c.encoded({rel:row['sha256'] for rel,row in SPEC['summary_followup']['payload']['sources'].items()})), 'completed_followup_source_required')
  followup_tx=c.parse(c.read(Path(SPEC['summary_followup']['stage'])/'transaction.json',followup_j['transaction_sha256']))
  need(followup_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_followup_spec_changed')"""
    remote = replace_once(remote, old, new)
    ast.parse(remote, feature_version=(3, 9))
    return remote


def payload_for(spec):
    return {relative: dict(row, base64=base64.b64encode(pinned(row['local_source'], row['sha256'])).decode('ascii'))
        for relative, row in spec[REVISION_KEY]['payload']['sources'].items()}


def execute_remote(remote, values, *, timeout=225):
    need(PAYLOAD_FINALIZED is True and APPROVED_PAYLOAD_SHA is not None, 'final_root_selected_v24_payload_required')
    approved_payload()
    current = (CANONICAL / 'spec.json').read_bytes()
    need(current in (pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA), encoded(values['SPEC'])),
         'unrelated_canonical_release_present')
    sys.path.insert(0, str(REPAIR / 'release_v18_candidate'))
    from v18_common import publisher_script, ssh_json
    return ssh_json(publisher_script(remote, values), timeout=timeout)
