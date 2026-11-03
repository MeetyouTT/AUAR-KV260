"""Public fake-model regressions for the isolated prompt-only candidate."""
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import replay_public_negation as replay

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=HERE.parents[4]
AURA=PROJECT/'aura'
candidate_path=HERE/'prompt_candidate/after/board/runtime/board_memory_policy.py'
assert replay.digest(candidate_path)=='ef45290c89ec72fcbcaf0a0ceac7dd76816ea5f3e59099477fe77f5d38b52825'
policy=replay.load('board.runtime.board_memory_policy',candidate_path)
original_tests=replay.load('public_observation_regressions',
    REPAIR/'memory_observation_candidate_r2/tests/test_observation_origin.py')
original_tests.AFTER=policy
diagnostics_tests=replay.load('public_negation_diagnostics_tests',HERE/'test_negation_diagnostics.py')
suite=unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(original_tests),
                         unittest.defaultTestLoader.loadTestsFromModule(diagnostics_tests)))
names=('test_long_closed_source_is_fully_covered_without_transcript_truncation',
       'test_partial_long_summary_never_publishes_or_deletes_source',
       'test_multiple_model_calls_renew_short_leases_only_between_requests',
       'test_irreducible_numeric_source_does_not_starve_other_closed_groups',
       'test_large_fragment_aggregate_is_reduced_without_exceeding_context',
       'test_fragment_boundaries_never_cut_decimal_number_or_protected_name')
namespace=dict(json=json,re=re,sqlite3=sqlite3,
    BoardMemoryStore=replay.STORE.BoardMemoryStore,BoardMemoryWorker=replay.STORE.BoardMemoryWorker,
    NUMBER=replay.STORE.NUMBER,NEGATION=replay.STORE.NEGATION,PLANNED=replay.STORE.PLANNED,
    BoardSummaryClient=policy.BoardSummaryClient,message_cost=policy.message_cost,
    Owner=replay.Owner,make_response=replay.make_response)
helper_file=AURA/'tests/framework/test_board_memory.py'
helper_tree=ast.parse(helper_file.read_text(encoding='utf8'))
helpers=[node for node in helper_tree.body if isinstance(node,ast.ClassDef) and node.name=='Clock'
    or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in ('SCOPE','OTHER') for target in node.targets)]
exec(compile(ast.Module(body=helpers,type_ignores=[]),str(helper_file),'exec'),namespace)
test_file=AURA/'tests/framework/test_board_memory_completion.py'
tree=ast.parse(test_file.read_text(encoding='utf8'))
nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))
       and node.name in names+('FragmentClient','long_text')]
test_proof={}
for node in nodes:
    node.decorator_list=[]
    assert not any(isinstance(item,ast.Name) and item.id=='pytest' for item in ast.walk(node))
    test_proof[node.name]=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
assert len(nodes)==len(names)+2
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(test_file),'exec'),namespace)
temporary_cleanup=[]
def regression(function,arguments):
    def run():
        temporary=tempfile.TemporaryDirectory(prefix='aura-public-prompt-regression-')
        connections=[]
        connect=sqlite3.connect
        def tracked_connect(*args,**kwargs):
            connection=connect(*args,**kwargs)
            connections.append(connection)
            return connection
        try:
            with patch.object(sqlite3,'connect',side_effect=tracked_connect):
                function(Path(temporary.name),**arguments)
        finally:
            # The unchanged repo fixtures use connection context managers,
            # which end transactions. Close their exact objects for Windows.
            for connection in connections:
                connection.close()
            try:
                temporary.cleanup()
            finally:
                temporary_cleanup.append(not Path(temporary.name).exists())
        assert not Path(temporary.name).exists()
    return run
completion_cases=0
for name in names:
    variants=({'mode':mode} for mode in ('failure','new-input','bad-number','call-limit')) if 'partial_long' in name else ({},)
    for arguments in variants:
        suite.addTest(unittest.FunctionTestCase(regression(namespace[name],arguments),
            description=name+(' '+arguments['mode'] if arguments else '')))
        completion_cases+=1
threads_before={thread.ident for thread in threading.enumerate()}
output=io.StringIO()
result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
leaked=[thread.name for thread in threading.enumerate() if thread.ident not in threads_before]
assert not leaked
loaded={}
mismatches=[]
for name,module in list(sys.modules.items()):
    filename=getattr(module,'__file__',None)
    if not filename:
        continue
    path=Path(filename)
    try:relative=path.relative_to(replay.BASE).as_posix()
    except ValueError:continue
    if relative not in replay.PINS:
        continue
    actual=replay.digest(path)
    loaded[name]=dict(relative=relative,sha256=actual)
    if actual!=replay.PINS[relative]:mismatches.append(relative)
report=dict(status='PASS' if result.wasSuccessful() and not mismatches else 'FAIL',
    source_sha256=replay.digest(candidate_path),
    tests_run=result.testsRun,completion_regression_cases=completion_cases,
    unittest_failures=len(result.failures),unittest_errors=len(result.errors),
    unittest_log=output.getvalue(),
    completion_original_function_ast_without_decorators=test_proof,
    completion_original_test_file_sha256=replay.digest(test_file),
    completion_runner='unittest calls original function AST and assertions with explicit tmp_path and four mode values',
    first_runner_attempt='pytest unavailable before completion-test invocation, runner changed without product-source changes',
    earlier_windows_fixture_cleanup='First AST runner had six SQLite fixture handle cleanup errors and one old imported dialogue dependency. Those results remain in PROMPT_REGRESSION.json. Exact fixture connections now close after original assertions, and H01 dialogue is bound before policy import.',
    loaded_dependency_proof=loaded,
    dependency_mismatches=mismatches,temporary_database_directories_removed=all(temporary_cleanup),
    leaked_threads=len(leaked),private_database_or_model_accessed=False,
    real_model_prompt_benefit_measured=False)
with (HERE/'PROMPT_REGRESSION_02.json').open('x',encoding='utf8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({key:report[key] for key in ('status','tests_run','completion_regression_cases',
    'unittest_failures','unittest_errors','dependency_mismatches',
    'temporary_database_directories_removed','real_model_prompt_benefit_measured')}))
raise SystemExit(0 if report['status']=='PASS' else 1)
