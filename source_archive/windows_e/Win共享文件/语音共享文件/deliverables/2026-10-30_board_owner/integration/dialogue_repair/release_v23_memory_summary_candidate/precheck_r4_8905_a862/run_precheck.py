"""Replay frozen R4 using public fixtures, without selecting or deploying it."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
PUBLISHER = HERE.parent
REPAIR = PUBLISHER.parent
CANDIDATE = REPAIR / 'memory_negation_v23_candidate_r4'
MANIFEST_SHA = 'dd19ca13cefeba8da28620954e77a47cb9b7d051e024115483a6c7c473e280a8'
HANDOFF_SHA = 'a9c1072d92e81623ce72fa10d45ec879b66cd9655c03f983ba1cc2cb77bec1c5'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(name, value):
    path = HERE / name
    with path.open('x', encoding='utf8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, sort_keys=True, indent=2)
        output.write('\n')
    return digest(path)


def load(name, path):
    definition = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(definition)
    sys.modules[name] = module
    definition.loader.exec_module(module)
    return module


def main():
    assert digest(CANDIDATE / 'HANDOFF.json') == HANDOFF_SHA
    assert digest(CANDIDATE / 'SOURCE_MANIFEST.json') == MANIFEST_SHA
    handoff = json.loads((CANDIDATE / 'HANDOFF.json').read_bytes())
    manifest = json.loads((CANDIDATE / 'SOURCE_MANIFEST.json').read_bytes())
    for relative, item in handoff['files'].items():
        assert digest(CANDIDATE / relative) == item['sha256'], relative
        assert (CANDIDATE / relative).stat().st_size == item['bytes'], relative
    review_path = REPAIR / 'performance_review_newboot/v23_publisher_independent_review/PUBLIC_REVIEW_RESULT.json'
    review = json.loads(review_path.read_bytes())
    assert review['status'] == 'PASS' and review['tests_run'] == 36
    for relative, expected in review['source_sha256'].items():
        assert digest(PUBLISHER / relative) == expected, relative

    public = load('run_public_tests', CANDIDATE / 'run_public_tests.py')
    contract = load('public_r4_contract_replay', CANDIDATE / 'test_r4_contract.py')
    observation = load('public_r4_observation_replay', REPAIR / 'memory_observation_candidate_r2/tests/test_observation_origin.py')
    observation.AFTER = public.POLICY
    original, ast_proof, cleanup = public.completion_regressions()
    suite = unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromModule(observation), original,
        unittest.defaultTestLoader.loadTestsFromTestCase(public.NegationTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(public.FragmentTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(public.QuestionAwareTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(public.PublicCaseTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(contract.R4ContractTests)))
    threads_before = {thread.ident for thread in threading.enumerate()}
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    leaked = [thread.ident for thread in threading.enumerate() if thread.ident not in threads_before]
    dependencies = {}
    mismatches = []
    for name, module in list(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        relative = name.replace('.', '/') + ('/__init__.py' if hasattr(module, '__path__') else '.py')
        if not filename or relative not in public.SPEC['component_sha256']:
            continue
        expected = manifest['sources'].get(relative, {}).get('after_sha256', public.SPEC['component_sha256'][relative])
        dependencies[name] = dict(relative=relative, sha256=digest(filename))
        if dependencies[name]['sha256'] != expected:
            mismatches.append(relative)
    assert result.wasSuccessful() and result.testsRun == 55 and not leaked and not mismatches and all(cleanup)
    (HERE / 'PRODUCT_TEST_OUTPUT.txt').write_text(output.getvalue(), encoding='utf8')
    write_json('PRODUCT_TEST_RESULT.json', dict(
        status='PASS', tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), loaded_dependencies=dependencies, dependency_mismatches=mismatches,
        leaked_threads=leaked, original_completion_ast=ast_proof, public_fixture_cleanup=all(cleanup),
        inference='PUBLIC_FAKE_ONLY', private_database_or_model_accessed=False, device_accessed=False,
        actual_source_selected=False, candidate_manifest_sha256=MANIFEST_SHA, candidate_handoff_sha256=HANDOFF_SHA))

    framework = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', 'test_framework', '-v'],
                               cwd=PUBLISHER, capture_output=True, text=True, encoding='utf8', timeout=90)
    assert framework.returncode == 0 and 'Ran 27 tests' in framework.stderr, framework.stderr
    write_json('FRAMEWORK_TEST_RESULT.json', dict(status='PASS', tests_run=27, returncode=framework.returncode,
                                                 output=framework.stdout + framework.stderr,
                                                 devices_accessed=False, model_accessed=False))

    sys.path.insert(0, str(PUBLISHER))
    import summary_common as common
    import apply_summary_closed
    import seal_summary
    assert common.PAYLOAD_FINALIZED is False and common.APPROVED_PAYLOAD_SHA is None
    assert not (PUBLISHER / 'APPROVED_PAYLOAD.json').exists()
    sources = {}
    for relative, row in manifest['sources'].items():
        raw = common.pinned(row['local_source'], row['after_sha256'])
        assert common.protected_source_ast(relative, raw) == common.protected_source_ast(relative, common.original_source(relative))
        sources[relative] = dict(before_sha256=row['before_sha256'], sha256=row['after_sha256'], local_source=row['local_source'])
    selected = dict(baseline_spec_sha256=common.BASE_SPEC_SHA, sources=sources,
                    decision=dict(path=str(CANDIDATE / 'HANDOFF.json'), sha256=HANDOFF_SHA))
    selected_raw = common.encoded(selected)
    selected_hash = common.sha(selected_raw)
    old_pinned = common.pinned

    def test_only_pinned(path, expected):
        if Path(path) == PUBLISHER / 'APPROVED_PAYLOAD.json':
            assert expected == selected_hash
            return selected_raw
        return old_pinned(path, expected)

    with patch.object(common, 'APPROVED_PAYLOAD_SHA', selected_hash), patch.object(common, 'pinned', test_only_pinned):
        base = common.baseline()
        spec = common.proposed()
        remote = dict(publish=common.publisher_remote(spec), apply=apply_summary_closed.build_remote(spec),
                      seal=seal_summary.build_remote(spec))
        for source in remote.values():
            ast.parse(source, feature_version=(3, 9))
        functions = lambda source: {node.name: ast.dump(node, include_attributes=False)
                                    for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
        assert functions(common.publisher_remote(base)) == functions(remote['publish'])
        changed = sorted(relative for relative in base['component_sha256'] if base['component_sha256'][relative] != spec['component_sha256'][relative])
        assert set(changed) == common.ALLOWED_PATHS and len(spec['component_sha256']) == 380
        for key in ('configuration_sha256', 'minor_prepared_configuration_path', 'camera_owner', 'camera_rebind',
                    'face_readback', 'expected_final_listening_enabled'):
            assert base[key] == spec[key], key
        write_json('SOURCE_FRAMEWORK_PRECHECK.json', dict(
            status='R4_SOURCE_AND_FRAMEWORK_PRECHECK_PASS', sources=manifest['sources'],
            component_count=380, changed_components=changed, other_components_unchanged=378,
            all_lifecycle_function_ast_unchanged=True, exact_r3_common_snippets_retained=True,
            exact_r4_suffix_reversal_verified=True, configuration_and_camera_22pin_authority_unchanged=True,
            hypothetical_startup_sha256_if_r4_selected=spec['startup_sha256'],
            unselected_precheck_remote_sha256={key: common.sha(value.encode()) for key, value in remote.items()},
            publisher_code_sha256=review['source_sha256'], independent_review_sha256=digest(review_path),
            test_only_in_memory_binding=True, actual_root_decision=None, payload_finalized=False,
            approved_payload_created=False, proposed_or_applied_spec_file_created=False,
            real_model_test_executed=False, device_or_private_database_accessed=False))
    write_json('PENDING_PAYLOAD.json', dict(status='UNSELECTED_R4_PENDING_ROOT_REAL_MODEL_AND_SEMANTIC_REVIEW',
                                           sources=sources, baseline_spec_sha256=common.BASE_SPEC_SHA,
                                           candidate_manifest_sha256=MANIFEST_SHA, candidate_handoff_sha256=HANDOFF_SHA,
                                           root_adoption_decision=None))
    for relative, item in handoff['files'].items():
        assert digest(CANDIDATE / relative) == item['sha256'], relative
    for relative, expected in review['source_sha256'].items():
        assert digest(PUBLISHER / relative) == expected, relative
    assert common.PAYLOAD_FINALIZED is False and common.APPROVED_PAYLOAD_SHA is None
    assert not (PUBLISHER / 'APPROVED_PAYLOAD.json').exists()
    files = {path.name: dict(sha256=digest(path), bytes=path.stat().st_size)
             for path in HERE.iterdir() if path.is_file()}
    handoff_hash = write_json('PRECHECK_HANDOFF.json', dict(
        status='R4_LOCAL_PRECHECK_PASSED_ROOT_REAL_MODEL_AND_SEMANTIC_SELECTION_PENDING', files=files,
        product_tests_passed=55, framework_tests_passed=27, loaded_dependencies=len(dependencies),
        candidate_frozen_files_unchanged=True, publisher_code_unchanged=True,
        all_lifecycle_function_ast_unchanged=True, actual_proposed_or_applied_spec_created=False,
        payload_finalized=False, approved_payload_sha256=None, root_adoption_decision=None,
        model_or_device_actions=False))
    print(json.dumps(dict(status='PASS', product_tests=55, framework_tests=27,
                         precheck_handoff_sha256=handoff_hash, execution_gate=False)))


if __name__ == '__main__':
    main()
