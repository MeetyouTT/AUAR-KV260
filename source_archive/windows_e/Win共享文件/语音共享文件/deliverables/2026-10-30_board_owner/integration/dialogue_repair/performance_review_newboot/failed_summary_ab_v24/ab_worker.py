"""One RAM source snapshot, two bounded summary calls, fixed metadata only."""
import ast
import copy
import json
import os
from pathlib import Path
import sys
import threading
import time

import base_worker as base


BASE_POLICY = 'a862cc22f6c23ae90d17ef06614cdf90fa0eb4605ad0a8b74766d102aad404aa'
CANDIDATE_POLICY = '80de72bce6d816a4da52db1dadee4a2c27c5c59242a1929c6316b76071c3105a'
OMIT_ARM_FIELDS = {'full_components_before', 'full_components_after', 'same_owners_before_after',
                   'saved_pause_preserved', 'database_connections', 'database_write_statements', 'hard_window_seconds'}
STATUSES = ('AB_DIAGNOSIS_COMPLETE', 'NO_ELIGIBLE_FAILED_GROUP', 'AB_GUARD_REFUSED',
            'AB_DIAGNOSTIC_FAILED', 'OWNED_CHILD_WINDOW_EXPIRED', 'OUTPUT_CONTRACT_REFUSED')


def empty_result(status='AB_DIAGNOSTIC_FAILED'):
    return dict(status=status, before=None, candidate=None, same_source_snapshot=0, calls=0,
        database_connections=0, database_write_statements=0, full_components_before=0,
        full_components_after=0, same_owners_before_after=0, saved_pause_preserved=0,
        original_messages_restored=0, candidate_only_messages_verified=0,
        hard_window_seconds=90, error_class='none')


def project_arm(value):
    base.validate_output(value)
    return {key: item for key, item in value.items() if key not in OMIT_ARM_FIELDS}


def validate_output(value):
    base.need(type(value) is dict and set(value) == set(empty_result()))
    base.need(value['status'] in STATUSES and value['error_class'] in base.CLASSES)
    for name in ('before', 'candidate'):
        arm = value[name]
        if arm is not None:
            expected = set(base.empty_result()) - OMIT_ARM_FIELDS
            base.need(type(arm) is dict and set(arm) == expected)
            base.validate_output(dict(base.empty_result(), **arm))
    for key, number in value.items():
        if key not in ('status', 'error_class', 'before', 'candidate'):
            base.need(type(number) is int and 0 <= number <= 380)
    base.need(value['calls'] <= 2 and value['database_connections'] <= 1
              and value['database_write_statements'] == 0 and value['hard_window_seconds'] == 90)
    return value


def reviewed_messages(original, candidate):
    base.need(base.digest(original) == BASE_POLICY and base.digest(candidate) == CANDIDATE_POLICY)
    trees = [ast.parse(raw, feature_version=(3, 9)) for raw in (original, candidate)]
    methods = []
    for tree in trees:
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardSummaryClient']
        base.need(len(classes) == 1)
        selected = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == '_messages']
        base.need(len(selected) == 1)
        methods.append(copy.deepcopy(selected[0]))
        selected[0].body = [ast.Pass()]
    base.need(ast.dump(trees[0], include_attributes=False) == ast.dump(trees[1], include_attributes=False))
    return methods[1]


def pair(prepared, memory, policy, actual, candidate, guard, cancelled_for_arm, result):
    source_snapshot = copy.deepcopy(prepared)
    old_method = policy.BoardSummaryClient._messages
    namespace = dict(policy.__dict__)
    exec(compile(ast.Module(body=[candidate], type_ignores=[]), '<reviewed-public-v24-messages>', 'exec'), namespace)
    new_method = namespace['_messages']
    exported = [dict(source=row['source'], text=row['text'], protected={key: row['metadata'][key]
                    for key in ('names', 'numbers', 'negated', 'status', 'evidence') if key in row['metadata']})
                for row in prepared['sources']]
    try:
        # Each arm must cover this complete source snapshot in its initial
        # request. A larger group is refused without selecting another task.
        for method in (old_method, new_method):
            policy.BoardSummaryClient._messages = method
            probe = policy.BoardSummaryClient(None, board_boot_id='private-ab-v24-fit',
                final_summary_max_utf8_bytes=301, max_calls=1, total_budget_ms=30000)
            base.need(probe._fits(exported, multipart=False))
        for label, method in (('before', old_method), ('candidate', new_method)):
            guard()
            base.need(prepared == source_snapshot)
            policy.BoardSummaryClient._messages = method
            arm = base.empty_result()
            try:
                base.diagnose(prepared, memory, policy, actual, guard, cancelled_for_arm(), arm)
            finally:
                result[label] = project_arm(arm)
                result['calls'] += arm['calls']
            base.need(prepared == source_snapshot and arm['calls'] == 1)
        result['same_source_snapshot'] = 1
    finally:
        policy.BoardSummaryClient._messages = old_method
        result['original_messages_restored'] = int(policy.BoardSummaryClient._messages is old_method)
    return result


def execute(arguments):
    import importlib
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    base.need(sys.platform.startswith('linux') and os.geteuid() == 0)
    sys.dont_write_bytecode = True
    result = empty_result()
    connected = [0]
    sys.addaudithook(base.readonly_audit(base.DATABASE.as_uri() + '?mode=ro', connected))
    stop, guard_failed = threading.Event(), threading.Event()
    monitor = None
    try:
        base.full_guard(arguments)
        base.fast_guard(arguments)
        result['full_components_before'] = 380
        runtime = Path(arguments['spec']['target']) / 'runtime/aura'
        with base.isolated_imports():
            sys.path.insert(0, str(runtime))
            memory = importlib.import_module('common.board_memory')
            policy = importlib.import_module('board.runtime.board_memory_policy')
            client_module = importlib.import_module('board.runtime.board_dialogue_client')
            for module in (memory, policy, client_module):
                relative = module.__name__.replace('.', '/') + '.py'
                base.need(Path(module.__file__).resolve() == runtime / relative
                          and base.digest(Path(module.__file__).read_bytes()) == arguments['spec']['component_sha256'][relative])
            candidate = reviewed_messages(Path(policy.__file__).read_bytes(), arguments['candidate_source'].encode('utf8'))
            base.need(arguments['candidate_sha256'] == CANDIDATE_POLICY)
            result['candidate_only_messages_verified'] = 1
            prepared = base.select_failed_group(base.DATABASE, memory)
            result['database_connections'] = connected[0]
            if prepared is None:
                result['status'] = 'NO_ELIGIBLE_FAILED_GROUP'
            else:
                def watch_guard():
                    while not stop.wait(.5):
                        try:
                            base.fast_guard(arguments)
                        except Exception:
                            guard_failed.set()
                            return
                monitor = threading.Thread(target=watch_guard, daemon=True)
                monitor.start()
                def cancelled_for_arm():
                    deadline = time.monotonic() + 30
                    return lambda: guard_failed.is_set() or time.monotonic() >= deadline
                pair(prepared, memory, policy, client_module.InferenceHttpClient('192.168.50.1', 8797),
                     candidate, lambda: base.fast_guard(arguments), cancelled_for_arm, result)
                result['status'] = 'AB_DIAGNOSIS_COMPLETE'
        stop.set()
        if monitor is not None:
            monitor.join(timeout=2.5)
        base.need(not guard_failed.is_set())
        base.full_guard(arguments)
        base.fast_guard(arguments)
        result.update(full_components_after=380, same_owners_before_after=1, saved_pause_preserved=1)
    except BaseException as error:
        result['status'] = 'AB_GUARD_REFUSED' if isinstance(error, base.Refused) or guard_failed.is_set() else 'AB_DIAGNOSTIC_FAILED'
        result['error_class'] = base.enum(type(error).__name__, base.CLASSES)
        result['database_connections'] = connected[0]
    finally:
        stop.set()
    return validate_output(result)


def child_main():
    output = os.dup(1)
    with open(os.devnull, 'wb') as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    result = empty_result()
    try:
        raw = sys.stdin.buffer.read(2097153)
        base.need(len(raw) <= 2097152)
        result = execute(base.parse(raw))
    except BaseException as error:
        result = empty_result()
        result['error_class'] = base.enum(type(error).__name__, base.CLASSES)
    os.write(output, json.dumps(validate_output(result), ensure_ascii=True, allow_nan=False).encode('ascii'))
    os.close(output)


if __name__ == '__main__':
    child_main()
