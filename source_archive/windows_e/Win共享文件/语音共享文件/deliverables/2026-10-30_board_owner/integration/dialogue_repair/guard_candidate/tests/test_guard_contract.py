"""Optimized read guard: reuse real synthetic Store/stream contracts, no ML I/O."""
import ast
from contextlib import contextmanager
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import sys

import pytest

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[5]
INTEGRATION = HERE.parents[2]
sys.path.insert(0, str(PROJECT / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FILE = HERE.parent / 'after/common/board_memory.py'
memory = load('common.joined_guard_candidate', FILE)
prepared = load('guard_reused_prepared_tests', INTEGRATION /
    'response_latency/memory_candidate/tests/test_prepared_turn.py')
prepared.FILE, prepared.memory = FILE, memory
stream = load('guard_reused_stream_tests', INTEGRATION /
    'response_latency/streaming_candidate/tests/test_stream_memory_contract.py')
stream.memory = memory
for module in (prepared, stream):
    for name, value in vars(module).items():
        if name.startswith('test_') and name != 'test_exact_base_has_only_new_read_method_and_no_other_ast_changes':
            globals()['test_reused_' + name[5:]] = value


def test_only_existing_prepared_method_changes_from_actual_store():
    before = HERE.parents[1] / 'before/common/board_memory.py'
    assert hashlib.sha256(before.read_bytes()).hexdigest() == '943bf88c05400c49c76a1aee68a0bb242cb929cee3e213bc21f465ac3ef77d46'
    old, new = ast.parse(before.read_bytes()), ast.parse(FILE.read_bytes())
    for tree in (old, new):
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardMemoryStore')
        cls.body = [node for node in cls.body if not (isinstance(node, ast.FunctionDef) and node.name == 'check_prepared_turn_current')]
    assert ast.dump(old) == ast.dump(new)


def test_exactly_one_connection_read_transaction_and_select_per_check(tmp_path, monkeypatch):
    store = prepared.make(tmp_path)
    prepared.prepared(store)
    before = Path(store.path).read_bytes()
    counts = dict(connect=0, close=0, SELECT=0, BEGIN=0, COMMIT=0, PRAGMA=0)
    original_connect = sqlite3.connect
    class Counted(sqlite3.Connection):
        def close(self):
            counts['close'] += 1
            return super().close()
    def trace(sql):
        first = sql.lstrip().split(None, 1)[0].upper()
        if first in counts: counts[first] += 1
    def connect(*args, **kwargs):
        counts['connect'] += 1
        kwargs['factory'] = Counted
        db = original_connect(*args, **kwargs)
        db.set_trace_callback(trace)
        return db
    monkeypatch.setattr(sqlite3, 'connect', connect)
    assert store.check_prepared_turn_current('public-turn', generation=1)
    assert counts == dict(connect=1, close=1, SELECT=1, BEGIN=1, COMMIT=1, PRAGMA=2)
    assert Path(store.path).read_bytes() == before


@pytest.mark.parametrize('bad_id', ['', 'x' * 161, 'bad id', 'bad/id', 'bad|id', '公开', 'good\x00tail', '[bad]', 'bad\\id'])
def test_batch_query_keeps_dependency_identifier_rejection(tmp_path, bad_id):
    store = prepared.make(tmp_path)
    store.append_event(prepared.SCOPE, 'public-source', 'user_said', '公开合成来源。')
    prepared.prepared(store, sources=['public-source'])
    # Deliberately corrupt the fixture's identifier consistently across rows.
    # Such IDs cannot be inserted through the Store's normal validated API.
    db = sqlite3.connect(store.path)
    try:
        db.execute('UPDATE bm_events SET event_id=? WHERE event_id=?', (bad_id, 'public-source'))
        db.execute('UPDATE bm_bodies SET event_id=? WHERE event_id=?', (bad_id, 'public-source'))
        db.execute('UPDATE bm_event_dependencies SET source_event_id=? WHERE source_event_id=?', (bad_id, 'public-source'))
        db.commit()
    finally:
        db.close()
    with pytest.raises((ValueError, memory.ScopeDenied)):
        store.check_prepared_turn_current('public-turn', generation=1)


def test_profile_scope_lock_is_held_before_opening_read_connection(tmp_path, monkeypatch):
    from common.profile_access import ProfileAccess
    access = ProfileAccess('a' * 64, clock=lambda: 10.)
    actor = dict(board_boot_id='public-boot', session_id='public-session')
    _, grant = access.issue('b' * 32, actor)
    store = prepared.make(tmp_path, profile_access=access)
    prepared.prepared(store, scope=dict(kind='profile', id='b' * 32, grant=grant))
    seen, inside = [], [False]
    original_use, original_db = access.use, store._db
    @contextmanager
    def use(value):
        with original_use(value) as selected:
            inside[0] = True
            try: yield selected
            finally: inside[0] = False
    @contextmanager
    def db(*args, **kwargs):
        assert inside[0]
        seen.append(True)
        with original_db(*args, **kwargs) as connection: yield connection
    monkeypatch.setattr(access, 'use', use)
    monkeypatch.setattr(store, '_db', db)
    assert store.check_prepared_turn_current('public-turn', generation=1)
    assert len(seen) == 1 and not inside[0]


def test_wrong_original_profile_grant_cannot_authorize_durable_owner(tmp_path):
    from common.profile_access import ProfileAccess
    access = ProfileAccess('a' * 64, clock=lambda: 10.)
    _, original = access.issue('b' * 32, dict(board_boot_id='public-boot', session_id='public-session'))
    store = prepared.make(tmp_path, profile_access=access)
    prepared.prepared(store, scope=dict(kind='profile', id='b' * 32, grant=original))
    _, other = access.issue('c' * 32, dict(board_boot_id='public-boot', session_id='other-session'))
    store._turn_grants['public-turn'] = other
    with pytest.raises(memory.ScopeDenied):
        store.check_prepared_turn_current('public-turn', generation=1)


def test_missing_dependency_row_is_rejected_by_left_join_not_sql_null(tmp_path):
    store = prepared.make(tmp_path)
    store.append_event(prepared.SCOPE, 'public-source', 'user_said', '公开来源。')
    prepared.prepared(store, sources=['public-source'])
    db = sqlite3.connect(store.path)
    try:
        db.execute("DELETE FROM bm_events WHERE event_id='public-source'")
        db.commit()
    finally:
        db.close()
    with pytest.raises(memory.ScopeDenied):
        store.check_prepared_turn_current('public-turn', generation=1)
