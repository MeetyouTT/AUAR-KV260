"""Independent, local, directed recheck of the 5ca source-alias fix only."""
import ast
import copy
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMERA = HERE.parent / 'camera'
SOURCE = CAMERA / 'validate_fresh_final_history_readonly.py'
OLD = CAMERA / 'fresh_history_alias_fix/validate_fresh_final_history_readonly.py.e92.before.bin'
NEW_SHA = '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9'
OLD_SHA = 'e92d8b0c461ff060d2e6d5e0aceef81c13ad1580cc3f66ad118b27c805b9f102'
old_raw, new_raw = OLD.read_bytes(), SOURCE.read_bytes()
assert hashlib.sha256(old_raw).hexdigest() == OLD_SHA
assert hashlib.sha256(new_raw).hexdigest() == NEW_SHA
old_tree, new_tree = ast.parse(old_raw), ast.parse(new_raw)
old_functions = {node.name: node for node in old_tree.body if isinstance(node, ast.FunctionDef)}
new_functions = {node.name: node for node in new_tree.body if isinstance(node, ast.FunctionDef)}
new_names = set(new_functions) - set(old_functions)
changed = {name for name in old_functions if ast.dump(old_functions[name]) != ast.dump(new_functions[name])}
assert new_names == {'reject_current_checkpoint_source'}
assert changed == {'referenced_value', 'validate_inputs'}
old_other = [node for node in old_tree.body if not isinstance(node, ast.FunctionDef)]
new_other = [node for node in new_tree.body if not isinstance(node, ast.FunctionDef)]
assert ast.dump(ast.Module(body=old_other, type_ignores=[])) == ast.dump(ast.Module(body=new_other, type_ignores=[]))

# Import the same pinned public in-memory fixture used in our original review.
# This does not invoke its unittest runner, CLI, guard or original_modules.
fixture_path = CAMERA / 'test_fresh_final_history_readonly.py'
assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == '69a3dc94e963b855a8a202268c96c71b2caff62878e1cef0ea2646a619fd07bb'
spec = importlib.util.spec_from_file_location('independent_fixed_alias_fixture', fixture_path)
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
candidate = fixture_module.candidate
results = []
negative = {'same_sha_sealed_copy', 'reformatted_same_owner_final', 'checkpoint_envelope', 'same_sha_stop_result_copy'}
cases = ('baseline', 'same_sha_sealed_copy', 'reformatted_same_owner_final', 'checkpoint_envelope',
         'same_sha_stop_result_copy', 'same_boot_other_pid', 'same_pid_other_birth', 'old_boot_archive_envelope')
for mode in cases:
    snap, expected, intent, result, document = fixture_module.fixture()
    original_legacy = candidate.LEGACY_SHA
    candidate.LEGACY_SHA = expected['history']['legacy_pin']['sha256']
    try:
        source_pin = None
        if mode != 'baseline':
            proof = snap.pinned(expected['history']['provenance_pin'])
            field, pointer = 'head', '/previous_kernel_history'
            source_document = copy.deepcopy(document)
            if mode == 'same_sha_sealed_copy':
                source_pin = snap.put('/synthetic/sealed-final-copy.json', source_document)
            elif mode == 'reformatted_same_owner_final':
                source_pin = snap.put('/synthetic/reformatted-final-copy.json', source_document,
                    (json.dumps(source_document, indent=2) + '\n').encode())
            elif mode == 'checkpoint_envelope':
                source_pin = snap.put('/synthetic/metadata-envelope.json',
                    {'schema': 'public-seal-envelope-1', 'checkpoint': source_document})
                pointer = '/checkpoint/previous_kernel_history'
            elif mode == 'same_sha_stop_result_copy':
                source_pin = snap.put('/synthetic/stopped-result-copy.json', result)
                field, pointer = 'boot_id', '/intent/boot_id'
            elif mode == 'same_boot_other_pid':
                source_document['seed']['source_pid'] += 1
                source_pin = snap.put('/synthetic/other-owner-document.json', source_document)
            elif mode == 'same_pid_other_birth':
                source_document['seed']['source_birth_ticks'] += 1
                source_pin = snap.put('/synthetic/other-birth-document.json', source_document)
            elif mode == 'old_boot_archive_envelope':
                archive = json.loads(snap.read(expected['history']['archives'][0]['path']))
                source_pin = snap.put('/synthetic/old-boot-envelope.json',
                    {'checkpoint': archive['checkpoint'], 'head': expected['history']['head']})
                pointer = '/head'
            proof['source_bindings'][field] = {'pin': source_pin, 'pointer': pointer}
            expected['history']['provenance_pin'] = snap.put('/synthetic/prestop-history.json', proof)
        accepted, error = False, None
        try:
            candidate.validate_inputs(expected, snap)
            accepted = True
        except (ValueError, TypeError, KeyError) as exc:
            error = type(exc).__name__ + ': ' + str(exc)
        intended = mode not in negative
        assert accepted == intended, (mode, accepted, error)
        if mode in ('same_sha_sealed_copy', 'same_sha_stop_result_copy'):
            assert error == 'ValueError: History source SHA aliases final/result/provenance'
        elif mode in negative:
            assert error == 'ValueError: History source contains current stopped-owner checkpoint'
        results.append({'case': mode, 'accepted': accepted, 'expected_accept': intended, 'passed': True,
                        'rejection': error})
    finally:
        candidate.LEGACY_SHA = original_legacy
assert SOURCE.read_bytes() == new_raw
report = {
    'schema': 'aura-independent-fresh-history-alias-fix-probes-1',
    'candidate_sha256': NEW_SHA, 'previous_candidate_sha256': OLD_SHA,
    'cases_run': len(results), 'passed': True, 'results': results,
    'new_function_names': sorted(new_names), 'changed_existing_function_names': sorted(changed),
    'all_other_functions_and_top_level_ast_unchanged': True,
    'test_scope': 'Only validate_inputs with the existing pinned public in-memory fixture and its synthetic legacy pin override. No original16 suite, guard, CLI, original_modules, SSH, board/proc/device/service/marker/model IO.',
    'candidate_modified': False, 'hostile_root_authentication_claimed': False,
}
with (HERE / 'FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_PROBES.json').open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
with (HERE / 'FRESH_HISTORY_ALIAS_FIX_INDEPENDENT_DIFF.txt').open('x', encoding='utf-8') as handle:
    handle.writelines(difflib.unified_diff(old_raw.decode().splitlines(keepends=True),
        new_raw.decode().splitlines(keepends=True), fromfile='e92.original', tofile='5ca.fixed'))
print(json.dumps(report))
