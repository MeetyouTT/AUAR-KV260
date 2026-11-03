"""Exact two-source memory follow-up to v22. Root selection is still required."""
import ast
import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PREVIOUS = REPAIR / 'release_v22_camera_rebind_candidate'
EVIDENCE = PREVIOUS / 'camera_rebind_evidence'
BASE_SPEC_SHA = 'ecdc034bd06cdd15bffe004a3ac1be3a6bc350dc3c879d91d3a19403f5c0f74a'
BASE_READY_SHA = '7ca292f5ad7d8e66de59b45f41cc2370e737e741c907db365e86485380297036'
BASE_MAPPING_SHA = '25762cca701602c8ea5d3c0fea649e0b89ebf220b9b66948fc68b11c05ba4a6f'
BASE_STARTUP_SHA = '48cb1a3a1fc62eae32c93a5be02df0bd60926cd064884a06990dd24b62762885'
BASE_MANIFEST_SHA = 'e3afb1f52a7fd8eb8382e50c7c084f22099930252359e098f4c594987163453b'
BASE_CONFIG_SHA = 'e0762cbfb88fd77238b5b1b3562fd00005bc505395867e96cfc8b1b6651fb135'
V22_COMMON_SHA = '40cf3ff5941489ed2151e0feb916188d3f82360c20b2f1ca7e64c15b11963291'
OLD_SOURCE_PINS = {
    'board/runtime/board_memory_policy.py': '410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5',
    'common/board_memory.py': '05095d249caf3598802d5951910b412affe167b508933c7e831e3ffacc4fc0d0',
}
ALLOWED_PATHS = set(OLD_SOURCE_PINS)
REVISION = 'memory-summary-v23'
PAYLOAD_FINALIZED = True
# Root supplies this SHA only after selecting a source using real public cases.
APPROVED_PAYLOAD_SHA = '7a44c5d9fa115fa4be319184b215b8f1c4fd0e92746bd9f9aee15a0991c3e809'
# Exact snippets from R3 manifest 447390dc and root-reviewed source 89057701.
# Binding these guards does not select a product or enable device execution.
R3_REVIEWED_POLAR_DECLARATION = r'''POLAR_QUESTION = re.compile(r"(?<![不没])(?:去不去|买不买|做不做|要不要|能不能|会不会|是不是|有没有|可不可以)")'''
R3_REVIEWED_NEGATION_DECLARATION = r'''NEGATION = re.compile(r"没有|不要|不能|不会|不是|尚未|未完成|不(?:去|买|做|要|能|会|是)|\b(?:not|never|no)\b|未准备|未能|未校准|未确认|未购买|未执行|无法|并非|并未|从未|未曾|不再|未喝", re.I)'''
R3_REVIEWED_NEGATION_BLOCK = r'''has_nonassertive_marker = (re.search(r"询问|提问|想知道|是否|能否|[?？]|无论|不管|不论", text) is not None
                          or POLAR_QUESTION.search(text) is not None)
source_negation_text = POLAR_QUESTION.sub(" ", source["text"]) if has_nonassertive_marker else source["text"]
summary_negation_text = POLAR_QUESTION.sub(" ", text)
if ((POLAR_QUESTION.search(source["text"]) and not has_nonassertive_marker)
        or ((meta.get("negated") is True or NEGATION.search(source_negation_text))
            and not NEGATION.search(summary_negation_text))):
    reasons.add("negation_missing")
'''
REJECTED_POLICY_SHAS = frozenset((
    '2488436c306fee4261cbbb0371e60617b8d32da3655d5dd7f697cd333ee9fe0f',
    '3d949b6669301967b6c043d01c94a9bba48d48a13c158534780784fd9e8bfe05',
))


def previous():
    path = PREVIOUS / 'rebind_common.py'
    import hashlib
    raw = path.read_bytes()
    if path.resolve() != path or path.is_symlink() or hashlib.sha256(raw).hexdigest() != V22_COMMON_SHA:
        raise ValueError('frozen_v22_publisher_changed')
    spec = importlib.util.spec_from_file_location('_frozen_v22_for_summary', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v22 = previous()
sha = v22.sha
encoded = v22.encoded
need = v22.need
pinned = v22.pinned
valid_sha = v22.valid_sha
write_new_json = v22.write_new_json


def baseline():
    value = json.loads(pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA))
    ready = json.loads(pinned(EVIDENCE / 'ready.json', BASE_READY_SHA))
    mapping = json.loads(pinned(EVIDENCE / 'source_mapping.json', BASE_MAPPING_SHA))
    v22.validate_spec(value)
    need(value['startup_sha256'] == BASE_STARTUP_SHA and value['source_manifest_sha256'] == BASE_MANIFEST_SHA
         and value['configuration_sha256'] == BASE_CONFIG_SHA and value['component_pins'] == 380
         and len(value['component_sha256']) == 380 and mapping['component_pins'] == value['component_sha256']
         and all(value['component_sha256'][relative] == pin for relative, pin in OLD_SOURCE_PINS.items()),
         'actual_v22_380_closure_required')
    need(ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed'] is True
         and ready['listening_enabled'] is False and ready['listening_state'] == 'PAUSED'
         and ready['physical_microphone_opened'] is False and mapping['current_publication_committed'] is True
         and value['expected_final_listening_enabled'] is False, 'actual_v22_ready_paused_required')
    need(value['camera_owner']['camera_pid'] == 229296 and value['camera_owner']['camera_start_ticks'] == '2474670'
         and value['camera_rebind']['binding']['written_proof']['candidate_pin_count'] == 22
         and value['face_readback']['sha256'] == 'dc6071426041e3589f3c3eb42fe32ee9b82aca5d6d6d26bf0ac58832cdd5f446',
         'restored_sameboot_camera_authority_required')
    return value


def original_source(relative):
    if relative == 'board/runtime/board_memory_policy.py':
        path = REPAIR / 'feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90' / relative
    else:
        need(relative == 'common/board_memory.py', 'exact_two_memory_sources_required')
        path = REPAIR / 'voice_visual_timeline_review_v90/after' / relative
    return pinned(path, OLD_SOURCE_PINS[relative])


def same_ast(left, right):
    return ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)


def reviewed_assignment(source, name):
    need(isinstance(source, str) and source, 'actual_r3_fixed_ast_review_pending')
    nodes = ast.parse(source, feature_version=(3, 9)).body
    need(len(nodes) == 1 and isinstance(nodes[0], ast.Assign) and len(nodes[0].targets) == 1
         and isinstance(nodes[0].targets[0], ast.Name) and nodes[0].targets[0].id == name,
         'one_exact_reviewed_regex_declaration_required')
    return nodes[0]


def original_negation_rule(tree):
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_compaction_text']
    need(len(functions) == 1, 'one_original_compaction_validator_required')
    loops = [node for node in functions[0].body if isinstance(node, ast.For)
             and isinstance(node.target, ast.Name) and node.target.id == 'source'
             and isinstance(node.iter, ast.Name) and node.iter.id == 'sources']
    need(len(loops) == 1, 'one_original_source_validation_loop_required')
    body = loops[0].body
    matches = [(index, node) for index, node in enumerate(body) if isinstance(node, ast.If)
               and any(isinstance(value, ast.Constant) and value.value == 'negation_missing' for value in ast.walk(node))]
    need(len(matches) == 1, 'one_original_negation_rejection_branch_required')
    index, rule = matches[0]
    return body, index, rule


def restore_reviewed_r3_negation_block(tree, negation_assignment, polar_assignment):
    need(same_ast(polar_assignment, reviewed_assignment(R3_REVIEWED_POLAR_DECLARATION, 'POLAR_QUESTION'))
         and same_ast(negation_assignment, reviewed_assignment(R3_REVIEWED_NEGATION_DECLARATION, 'NEGATION')),
         'r3_fixed_pattern_declaration_changed')
    need(isinstance(R3_REVIEWED_NEGATION_BLOCK, str) and R3_REVIEWED_NEGATION_BLOCK,
         'actual_r3_fixed_ast_review_pending')
    reviewed = ast.parse(R3_REVIEWED_NEGATION_BLOCK, feature_version=(3, 9)).body
    names = ('has_nonassertive_marker', 'source_negation_text', 'summary_negation_text')
    need(len(reviewed) == 4 and isinstance(reviewed[3], ast.If)
         and all(isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name
                 for node, name in zip(reviewed[:3], names)), 'exact_three_locals_and_negation_rule_required')
    original_tree = ast.parse(original_source('common/board_memory.py'), feature_version=(3, 9))
    _, _, original_rule = original_negation_rule(original_tree)
    need(same_ast(ast.Module(body=reviewed[3].body, type_ignores=[]), ast.Module(body=original_rule.body, type_ignores=[]))
         and same_ast(ast.Module(body=reviewed[3].orelse, type_ignores=[]), ast.Module(body=original_rule.orelse, type_ignores=[])),
         'original_negation_rejection_action_must_remain_unchanged')
    body, index, _ = original_negation_rule(tree)
    need(index >= 3 and same_ast(ast.Module(body=body[index-3:index+1], type_ignores=[]),
                                ast.Module(body=reviewed, type_ignores=[])), 'r3_negation_text_handling_diff_changed')
    body[index-3:index+1] = [copy.deepcopy(original_rule)]
    tree.body.remove(polar_assignment)


def protected_source_ast(relative, raw):
    tree = ast.parse(raw, feature_version=(3, 9))
    if relative == 'common/board_memory.py':
        assignments = [node for node in tree.body if isinstance(node, ast.Assign) and len(node.targets) == 1
                       and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'NEGATION']
        need(len(assignments) == 1, 'one_original_negation_pattern_required')
        polar = [node for node in tree.body if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'POLAR_QUESTION']
        need(len(polar) <= 1, 'at_most_one_fixed_polar_question_pattern_required')
        if polar:
            restore_reviewed_r3_negation_block(tree, assignments[0], polar[0])
        assignments[0].value = ast.Constant(value=None)
        return ast.dump(tree, include_attributes=False)
    need(relative == 'board/runtime/board_memory_policy.py', 'exact_two_memory_sources_required')
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == 'common.board_memory']
    need(len(imports) == 1, 'one_original_memory_import_required')
    polar_imports = [alias for alias in imports[0].names if alias.name == 'POLAR_QUESTION']
    need(len(polar_imports) <= 1 and all(alias.asname is None for alias in polar_imports),
         'only_fixed_unaliased_polar_question_import_allowed')
    if polar_imports:
        reviewed_assignment(R3_REVIEWED_POLAR_DECLARATION, 'POLAR_QUESTION')
        imports[0].names.remove(polar_imports[0])
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardSummaryClient']
    need(len(classes) == 1, 'original_summary_client_required')
    methods = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name in ('_messages', '_fragments')]
    need(len(methods) == 2, 'original_summary_messages_and_fragments_required')
    for method in methods:
        method.body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def approved_payload():
    need(APPROVED_PAYLOAD_SHA is not None, 'root_real_model_selection_pending')
    value = json.loads(pinned(HERE / 'APPROVED_PAYLOAD.json', APPROVED_PAYLOAD_SHA))
    need(set(value) == {'baseline_spec_sha256', 'sources', 'decision'}
         and value['baseline_spec_sha256'] == BASE_SPEC_SHA and set(value['sources']) == ALLOWED_PATHS,
         'exact_two_source_root_selection_required')
    decision = value['decision']
    need(set(decision) == {'path', 'sha256'}, 'pinned_actual_root_decision_required')
    pinned(decision['path'], decision['sha256'])
    for relative, row in value['sources'].items():
        need(set(row) == {'before_sha256', 'sha256', 'local_source'}
             and row['before_sha256'] == OLD_SOURCE_PINS[relative] and valid_sha(row['sha256'])
             and row['sha256'] != row['before_sha256'], 'exact_selected_memory_source_required')
        need(relative != 'board/runtime/board_memory_policy.py' or row['sha256'] not in REJECTED_POLICY_SHAS,
             'real_model_rejected_prompt_candidate_cannot_be_selected')
        raw = pinned(row['local_source'], row['sha256'])
        need(0 < len(raw) < 2097152 and protected_source_ast(relative, raw) == protected_source_ast(relative, original_source(relative)),
             'store_schema_commit_cleanup_permissions_deadlines_and_other_ast_must_remain_unchanged')
    return value


def startup_for(spec):
    return v22.startup_for(spec)


def proposed():
    selected = approved_payload()
    spec = baseline()
    for relative, row in selected['sources'].items():
        spec['component_sha256'][relative] = row['sha256']
        spec['release_sources'][relative] = row['sha256']
    spec['startup_sha256'] = sha(encoded(startup_for(spec)))
    spec['source_manifest_sha256'] = '0' * 64
    payload_sha = sha(encoded({relative: row['sha256'] for relative, row in selected['sources'].items()}))
    stage = v22.CONTROL + '/' + REVISION + '-' + payload_sha[:16]
    spec['summary_revision'] = dict(state='PROPOSED', name=REVISION, stage=stage, payload=selected,
                                     previous_spec_sha256=BASE_SPEC_SHA)
    return json.loads(encoded(spec))


def validate_spec(spec, *, allow_baseline=False, allow_proposed=False):
    if 'summary_revision' not in spec:
        need(allow_baseline and spec == baseline(), 'exact_actual_v22_baseline_required')
        return spec
    expected = proposed()
    if spec['summary_revision']['state'] == 'APPLIED':
        need(valid_sha(spec['source_manifest_sha256']) and spec['source_manifest_sha256'] != '0' * 64,
             'actual_summary_manifest_required')
        expected['summary_revision']['state'] = 'APPLIED'
        expected['source_manifest_sha256'] = spec['source_manifest_sha256']
    else:
        need(allow_proposed and spec['summary_revision']['state'] == 'PROPOSED', 'applied_summary_revision_required')
    need(spec == expected, 'only_exact_selected_summary_source_allowed')
    return spec


def publisher_remote(spec):
    validate_spec(spec, allow_baseline=True, allow_proposed=True)
    base = baseline()
    remote = v22.publisher_remote(base)
    if 'summary_revision' not in spec:
        return remote
    remote = v22.replace_node(remote, 'EXPECTED_STARTUP', 'EXPECTED_STARTUP=' + repr(startup_for(spec)))
    original = "  need(rebind_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_rebind_spec_changed')"
    need(remote.count(original) == 1, 'unique_original_rebind_transaction_guard_required')
    # The camera transaction attests the actual v22 spec. The independent v23
    # source transaction below attests the current full spec.
    replacement = "  need(rebind_tx.get('applied_spec_sha256')==" + repr(BASE_SPEC_SHA) + ", 'completed_rebind_spec_changed')\n"
    replacement += """  summary_j=rebind_j.get('summary_revision',{})
  need(summary_j.get('state')=='APPLIED' and summary_j.get('stage')==SPEC['summary_revision']['stage']
       and summary_j.get('payload_sha256')==c.sha(c.encoded({rel:row['sha256'] for rel,row in SPEC['summary_revision']['payload']['sources'].items()})), 'completed_summary_source_required')
  summary_tx=c.parse(c.read(Path(SPEC['summary_revision']['stage'])/'transaction.json',summary_j['transaction_sha256']))
  need(summary_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_summary_spec_changed')"""
    remote = remote.replace(original, replacement)
    ast.parse(remote, feature_version=(3, 9))
    return remote


def payload_for(spec):
    return {relative: dict(row, base64=base64.b64encode(pinned(row['local_source'], row['sha256'])).decode('ascii'))
            for relative, row in spec['summary_revision']['payload']['sources'].items()}


def execute_remote(remote, values, *, timeout=225):
    need(PAYLOAD_FINALIZED is True and APPROVED_PAYLOAD_SHA is not None, 'final_root_selected_payload_required')
    approved_payload()
    sys.path.insert(0, str(REPAIR / 'release_v18_candidate'))
    from v18_common import publisher_script, ssh_json
    return ssh_json(publisher_script(remote, values), timeout=timeout)
