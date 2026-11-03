"""Directed source-alias fix probes only; do not run the unchanged16-test suite.

Uses the existing public RAM fixture; never guard/original_modules/CLI/SSH.
Preserves the e92 evidence and asserts every unrelated candidate AST is intact.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'validate_fresh_final_history_readonly.py'
BEFORE = HERE / 'fresh_history_alias_fix/validate_fresh_final_history_readonly.py.e92.before.bin'
OLD_SHA = 'e92d8b0c461ff060d2e6d5e0aceef81c13ad1580cc3f66ad118b27c805b9f102'
assert hashlib.sha256(BEFORE.read_bytes()).hexdigest() == OLD_SHA
new_source = SOURCE.read_bytes()
new_sha = hashlib.sha256(new_source).hexdigest()
old_tree, new_tree = ast.parse(BEFORE.read_bytes()), ast.parse(new_source)


def dump(nodes):
    return ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False)


changed = {'reject_current_checkpoint_source', 'referenced_value', 'validate_inputs'}
retained = lambda tree: [node for node in tree.body if not isinstance(node, ast.FunctionDef) or node.name not in changed]
assert dump(retained(old_tree)) == dump(retained(new_tree)), 'Unexpected change outside alias-source gate'


class NormalizeInputs(ast.NodeTransformer):
    def visit_Assign(self, node):
        if any(isinstance(target, ast.Name) and target.id == 'forbidden_shas' for target in node.targets):
            return None
        return self.generic_visit(node)

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == 'referenced_value':
            node.args = node.args[:3]
        return node


old_inputs = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_inputs')
new_inputs = next(node for node in new_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_inputs')
assert ast.dump(old_inputs) == ast.dump(NormalizeInputs().visit(copy.deepcopy(new_inputs)))
old_reference = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'referenced_value')
new_reference = copy.deepcopy(next(node for node in new_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'referenced_value'))
new_reference.args.args = new_reference.args.args[:3]
new_reference.body = [node for node in new_reference.body
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and (
        isinstance(node.value.func, ast.Name) and node.value.func.id == 'reject_current_checkpoint_source'
        or isinstance(node.value.func, ast.Name) and node.value.func.id == 'require'
        and any(isinstance(name, ast.Name) and name.id == 'forbidden_shas' for name in ast.walk(node.value))))]
assert ast.dump(old_reference) == ast.dump(new_reference)

fixture_path = HERE / 'test_fresh_final_history_readonly.py'
assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == '69a3dc94e963b855a8a202268c96c71b2caff62878e1cef0ea2646a619fd07bb'
spec = importlib.util.spec_from_file_location('fresh_history_alias_fix_ram_fixture', fixture_path)
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
candidate = fixture_module.candidate
results = []
negative = {'same_sha_sealed_copy', 'reformatted_same_owner_final', 'checkpoint_envelope', 'stop_result_same_sha_copy'}
cases = ('baseline', 'same_sha_sealed_copy', 'reformatted_same_owner_final', 'checkpoint_envelope',
         'stop_result_same_sha_copy', 'same_boot_different_pid', 'same_boot_different_birth', 'different_boot_archive_envelope')
for case in cases:
    snapshot, expected, intent, result, document = fixture_module.fixture()
    original_legacy = candidate.LEGACY_SHA
    candidate.LEGACY_SHA = expected['history']['legacy_pin']['sha256']
    try:
        source_pin = None
        if case != 'baseline':
            proof = snapshot.pinned(expected['history']['provenance_pin'])
            field, pointer = 'head', '/previous_kernel_history'
            if case == 'same_sha_sealed_copy':
                source_pin = snapshot.put('/synthetic/sealed-final-copy.json', document)
            elif case == 'reformatted_same_owner_final':
                source_pin = snapshot.put('/synthetic/reformatted-final-copy.json', document,
                                          (json.dumps(document, indent=2) + '\n').encode())
            elif case == 'checkpoint_envelope':
                source_pin = snapshot.put('/synthetic/metadata-envelope.json', {'schema': 'public-seal-envelope-1', 'checkpoint': copy.deepcopy(document)})
                pointer = '/checkpoint/previous_kernel_history'
            elif case == 'stop_result_same_sha_copy':
                source_pin = snapshot.put('/synthetic/normal-stop-result-copy.json', result)
                field, pointer = 'boot_id', '/intent/boot_id'
            elif case in ('same_boot_different_pid', 'same_boot_different_birth'):
                prior = copy.deepcopy(document)
                prior['seed']['source_pid' if case.endswith('_pid') else 'source_birth_ticks'] += 1
                source_pin = snapshot.put('/synthetic/independent-prior-owner.json', prior)
            else:
                first_archive = json.loads(snapshot.read(expected['history']['archives'][0]['path']))
                source_pin = snapshot.put('/synthetic/prior-boot-archive-receipt.json',
                    {'schema': 'public-history-context-1', 'head': expected['history']['head'], 'checkpoint': first_archive['checkpoint']})
                pointer = '/head'
            proof['source_bindings'][field] = {'pin': source_pin, 'pointer': pointer}
            expected['history']['provenance_pin'] = snapshot.put('/synthetic/prestop-history.json', proof)
        accepted, reason = False, None
        try:
            candidate.validate_inputs(expected, snapshot)
            accepted = True
        except (ValueError, KeyError, TypeError) as exc:
            reason = type(exc).__name__ + ': ' + str(exc)
        should_accept = case not in negative
        assert accepted == should_accept, (case, accepted, reason)
        results.append(dict(case=case, accepted=accepted, expected_accept=should_accept, passed=True, rejection=reason,
                            source_sha_equals_final=source_pin['sha256'] == expected['checkpoint_pin']['sha256'] if source_pin else None))
    finally:
        candidate.LEGACY_SHA = original_legacy

assert SOURCE.read_bytes() == new_source
report = dict(candidate_sha256=new_sha, original_candidate_sha256=OLD_SHA, results=results,
              cases_run=len(results), passed=True, unrelated_ast_unchanged=True,
              validate_inputs_changes_only_alias_hash_set_and_forwarding=True,
              referenced_value_changes_only_alias_gates=True, existing16_tests_rerun=False,
              fixture_source_unchanged=True, source_and_reports_preserved_in='fresh_history_alias_fix',
              board_ssh_proc_marker_service_or_cli_io=False, actual_original_modules_loader_run=False,
              native_context_or_aura_cdll_created=False, hostile_root_authentication_claimed=False)
(HERE / 'FRESH_HISTORY_ALIAS_FIX_PROBES.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
