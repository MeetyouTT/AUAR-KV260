"""Finite read sessions: synthetic databases/fake models only, no devices."""
from contextlib import contextmanager
import ast
import importlib.util
from pathlib import Path
import sqlite3
import sys
import threading
import time
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[5] / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


memory = load('common.guard_session_test_memory', HERE.parent / 'after/common/board_memory.py')
prior = load('guard_session_prior_tests', INTEGRATION / 'dialogue_repair/guard_candidate/tests/test_guard_contract.py')
jobs_module = load('board.runtime.audio.guard_session_test_jobs', HERE.parent / 'after/board/runtime/audio/board_dialogue_jobs.py')
prior.memory, prior.FILE = memory, HERE.parent / 'after/common/board_memory.py'
prior.prepared.memory, prior.prepared.FILE = memory, prior.FILE
prior.stream.memory = memory
jobs_module.PlaybackPlan, jobs_module.StaleGeneration = prior.stream.dialogue.PlaybackPlan, prior.stream.dialogue.StaleGeneration
prior.stream.jobs_module = jobs_module
for name, value in vars(prior).items():
    if name.startswith('test_') and name != 'test_only_existing_prepared_method_changes_from_actual_store':
        globals()['test_prior_' + name[5:]] = value


def prepared_store(tmp_path):
    store = prior.prepared.make(tmp_path)
    prior.prepared.prepared(store)
    return store


def track_connections(monkeypatch):
    connections = []
    original = sqlite3.connect
    class Tracked(sqlite3.Connection):
        def close(self):
            self.closed_count += 1
            return super().close()
    def connect(*args, **kwargs):
        kwargs['factory'] = Tracked
        db = original(*args, **kwargs)
        db.closed_count, db.statements = 0, []
        db.set_trace_callback(lambda sql: db.statements.append(sql.lstrip().split(None, 1)[0].upper()))
        if kwargs.get('uri'): connections.append(db)
        return db
    monkeypatch.setattr(sqlite3, 'connect', connect)
    return connections


def test_connection_reused_but_every_call_has_new_transaction_and_no_bytes_change(tmp_path, monkeypatch):
    store = prepared_store(tmp_path)
    before = Path(store.path).read_bytes()
    connections = track_connections(monkeypatch)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        for _ in range(12):
            assert check()
            assert check._connection.in_transaction is False
        assert len(connections) == 1 and connections[0].closed_count == 0
        assert connections[0].statements.count('SELECT') == 12
        assert connections[0].statements.count('BEGIN') == 12
        assert connections[0].statements.count('COMMIT') == 12
        assert connections[0].statements.count('PRAGMA') == 2
    assert connections[0].closed_count == 1
    assert check._closed and check._connection is None
    assert Path(store.path).read_bytes() == before
    with pytest.raises(memory.StaleTurn): check()


def test_external_clear_is_seen_without_cached_snapshot_and_failed_session_closes(tmp_path):
    store = prepared_store(tmp_path)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        assert check()
        other = memory.BoardMemoryStore(store.path, clock=lambda: 1001.)
        other.clear(prior.prepared.SCOPE)
        with pytest.raises(memory.StaleTurn): check()
        assert check._closed and check._connection is None


def test_session_connection_is_enforced_readonly(tmp_path):
    store = prepared_store(tmp_path)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        with pytest.raises(sqlite3.OperationalError):
            check._connection.execute('CREATE TABLE forbidden_probe(value)')
        assert check()


def test_foreign_thread_check_and_close_reject_without_leaking_owner_cleanup(tmp_path):
    store = prepared_store(tmp_path)
    errors = []
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        def foreign():
            for action in (check, check.close):
                try: action()
                except Exception as exc: errors.append(type(exc))
        thread = threading.Thread(target=foreign)
        thread.start(); thread.join(timeout=2.)
        assert not thread.is_alive()
        assert errors == [RuntimeError, RuntimeError]
        assert check() and not check._closed
    assert check._closed


def test_context_body_error_closes_and_operational_failure_rolls_back_then_closes(tmp_path, monkeypatch):
    store = prepared_store(tmp_path)
    with pytest.raises(RuntimeError):
        with store.prepared_turn_checker('public-turn', generation=1) as check:
            assert check()
            raise RuntimeError('public-fixture-body-error')
    assert check._closed and check._connection is None
    def fail(*args): raise sqlite3.OperationalError('database is locked')
    monkeypatch.setattr(store, '_check_prepared_snapshot', fail)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        with pytest.raises(memory.MemoryBusy): check()
        assert check._closed
    # No reader lock survives the failed transaction.
    db = sqlite3.connect(store.path, timeout=.1)
    try:
        db.execute('BEGIN EXCLUSIVE'); db.rollback()
    finally: db.close()


@pytest.mark.parametrize('change', ['missing', 'inode', 'symlink'])
def test_database_path_identity_changes_fail_closed_before_next_transaction(tmp_path, monkeypatch, change):
    store = prepared_store(tmp_path)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        assert check()
        original = memory.os.stat
        def changed(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path) != store.path: return value
            if change == 'missing': raise FileNotFoundError()
            return SimpleNamespace(st_dev=value.st_dev, st_ino=value.st_ino + (change == 'inode'),
                                   st_mode=0o120777 if change == 'symlink' else value.st_mode)
        monkeypatch.setattr(memory.os, 'stat', changed)
        with pytest.raises(memory.StaleTurn): check()
        assert check._closed and check._connection is None


def test_normal_writes_change_size_mtime_without_rejecting_unchanged_source(tmp_path):
    store = prepared_store(tmp_path)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        assert check()
        other = memory.BoardMemoryStore(store.path, clock=lambda: 1001.)
        other.append_event(dict(kind='conversation', id='other-public-scope'),
                           'unrelated-public-event', 'user_said', '公开资料。' * 1000)
        assert check()


def test_profile_lock_precedes_each_begin_and_is_released_between_checks(tmp_path, monkeypatch):
    from common.profile_access import ProfileAccess
    access = ProfileAccess('a' * 64, clock=lambda: 10.)
    actor = dict(board_boot_id='public-boot', session_id='public-session')
    _, grant = access.issue('b' * 32, actor)
    store = prior.prepared.make(tmp_path, profile_access=access)
    prior.prepared.prepared(store, scope=dict(kind='profile', id='b' * 32, grant=grant))
    inside = [False]
    original_use = access.use
    @contextmanager
    def use(value):
        with original_use(value) as selected:
            inside[0] = True
            try: yield selected
            finally: inside[0] = False
    monkeypatch.setattr(access, 'use', use)
    with store.prepared_turn_checker('public-turn', generation=1) as check:
        begins = []
        def trace(sql):
            if sql.startswith('BEGIN'): begins.append(inside[0])
        check._connection.set_trace_callback(trace)
        assert check() and not inside[0]
        assert check() and not inside[0]
        assert begins == [True, True]
        access.revoke(actor)
        with pytest.raises(PermissionError): check()
        assert check._closed


@pytest.mark.parametrize('outcome', ['success', 'tts_failure', 'cancel'])
def test_jobs_owns_one_session_and_finally_closes_all_outcomes(tmp_path, outcome):
    fx = prior.stream.fixture(tmp_path)
    sessions = []
    original_factory = fx.store.prepared_turn_checker
    def factory(*args, **kwargs):
        session = original_factory(*args, **kwargs)
        sessions.append(session)
        return session
    fx.store.prepared_turn_checker = factory
    jobs = prior.stream.make_jobs(fx)
    if outcome == 'tts_failure': fx.models.fail_tts = 2
    if outcome == 'cancel':
        original_put = jobs._put
        def put(job, value, **kwargs):
            original_put(job, value, **kwargs)
            if value.get('channel_event', {}).get('kind') == 'audio': jobs.cancel()
        jobs._put = put
    metadata = jobs.submit(prior.stream.clip())
    assert jobs.run_next()
    assert len(sessions) == 1 and sessions[0]._closed and sessions[0]._connection is None
    values = prior.stream.drain(jobs)
    if outcome == 'success':
        result = next(v['network_complete'] for v in values if 'network_complete' in v)
        assert prior.stream.assistant_messages(fx) == []
        jobs.acknowledge(metadata, result); jobs.drain_actions()
        assert jobs.last_ack['committed']
    else:
        assert not any('network_complete' in v for v in values)
        jobs.drain_actions()
        assert jobs.last_ack is None
    metrics = jobs.public()['diagnostics']
    assert metrics['guard_thread_cpu_total_ms'] >= 0
    assert metrics['guard_thread_cpu_max_ms'] <= metrics['guard_thread_cpu_total_ms']


def test_cpu_diagnostic_excludes_sleep_from_thread_cpu(tmp_path):
    fx = prior.stream.fixture(tmp_path)
    jobs = prior.stream.make_jobs(fx)
    jobs.submit(prior.stream.clip())
    job = jobs.waiting
    jobs._put(job, dict(public_packet=True), admission_guard=lambda: time.sleep(.01))
    assert job.diagnostics['guard_total_ms'] >= 8.
    assert job.diagnostics['guard_thread_cpu_total_ms'] < job.diagnostics['guard_total_ms']


def test_entry_pragma_failure_closes_before_exitstack_can_register(tmp_path, monkeypatch):
    store = prepared_store(tmp_path)
    original_connect, opened = sqlite3.connect, []
    class Failing(sqlite3.Connection):
        def execute(self, sql, *args):
            if sql == 'PRAGMA secure_delete=ON': raise OSError('public-entry-fixture')
            return super().execute(sql, *args)
        def close(self):
            self.was_closed = True
            return super().close()
    def connect(*args, **kwargs):
        kwargs['factory'] = Failing
        db = original_connect(*args, **kwargs)
        db.was_closed = False; opened.append(db)
        return db
    monkeypatch.setattr(sqlite3, 'connect', connect)
    check = store.prepared_turn_checker('public-turn', generation=1)
    with pytest.raises(OSError): check.__enter__()
    assert check._closed and check._connection is None and opened[0].was_closed


def test_partial_close_failure_retains_handle_for_owner_outer_cleanup_retry(tmp_path, monkeypatch):
    store = prepared_store(tmp_path)
    original_connect, opened = sqlite3.connect, []
    class FailingOnce(sqlite3.Connection):
        def close(self):
            self.close_attempts += 1
            if self.close_attempts == 1: raise RuntimeError('public-close-fixture')
            return super().close()
    def connect(*args, **kwargs):
        kwargs['factory'] = FailingOnce
        db = original_connect(*args, **kwargs)
        db.close_attempts = 0; opened.append(db)
        return db
    def rejected(*args): raise ValueError('public-read-fixture')
    monkeypatch.setattr(sqlite3, 'connect', connect)
    monkeypatch.setattr(store, '_check_prepared_snapshot', rejected)
    with pytest.raises(RuntimeError):
        with store.prepared_turn_checker('public-turn', generation=1) as check: check()
    assert opened[0].close_attempts == 2 and check._connection is None and check._closed


def test_other_store_ast_and_exact_joined_validation_are_preserved():
    old = ast.parse((INTEGRATION / 'dialogue_repair/guard_candidate/after/common/board_memory.py').read_bytes())
    new = ast.parse((HERE.parent / 'after/common/board_memory.py').read_bytes())
    classes = [next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardMemoryStore') for tree in (old, new)]
    method = next(n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == 'check_prepared_turn_current')
    helper = next(n for n in classes[1].body if isinstance(n, ast.FunctionDef) and n.name == '_check_prepared_snapshot')
    original_body = next(n for n in method.body if isinstance(n, ast.With)).body
    for body in (original_body, helper.body):
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and 'SELECT t.*' in node.value:
                node.value = ' '.join(node.value.split())
    assert ast.dump(ast.Module(body=original_body, type_ignores=[])) == ast.dump(ast.Module(body=helper.body, type_ignores=[]))
    changed = {'check_prepared_turn_current', '_prepared_read_authority', '_check_prepared_snapshot', 'prepared_turn_checker'}
    for cls in classes:
        cls.body = [n for n in cls.body if not (isinstance(n, ast.FunctionDef) and n.name in changed)]
    new.body = [n for n in new.body if not (isinstance(n, ast.ClassDef) and n.name == '_PreparedTurnReadSession')
                and not (isinstance(n, ast.Import) and len(n.names) == 1 and n.names[0].name in ('os', 'stat'))]
    assert ast.dump(old) == ast.dump(new)
