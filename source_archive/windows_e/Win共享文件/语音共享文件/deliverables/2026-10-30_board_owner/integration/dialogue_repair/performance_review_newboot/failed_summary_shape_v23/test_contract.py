"""Public SQLite and fake-wire tests. No Store instance, device or model call."""
import contextlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import worker
import run_diagnose


HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parent.parent / 'memory_negation_v23_candidate_r4/run_public_tests.py'
definition = importlib.util.spec_from_file_location('_diagnostic_public_sources', PUBLIC)
public = importlib.util.module_from_spec(definition)
definition.loader.exec_module(public)


@contextlib.contextmanager
def database(path):
    db = sqlite3.connect(path)
    db.executescript('''PRAGMA application_id=1096110658; PRAGMA user_version=1;
    CREATE TABLE bm_tasks(task_id TEXT,scope_kind TEXT,scope_id TEXT,topic TEXT,start_utc REAL,
        end_utc REAL,status TEXT,error_code TEXT,created_utc REAL);
    CREATE TABLE bm_task_sources(task_id TEXT,event_id TEXT,revision INTEGER,body_hash TEXT);
    CREATE TABLE bm_events(event_id TEXT,scope_kind TEXT,scope_id TEXT,topic TEXT,source TEXT,
        state TEXT,closed_utc REAL,revision INTEGER,body_hash TEXT,compacted_summary_id TEXT,
        reserved_task TEXT,recorded_utc REAL,occurred_utc REAL,playback TEXT,metadata TEXT);
    CREATE TABLE bm_bodies(event_id TEXT,text TEXT);''')
    try:
        yield db
        db.commit()
    finally:
        db.close()


def add_task(db, key, texts, created=1):
    db.execute('INSERT INTO bm_tasks VALUES(?,?,?,?,?,?,?,?,?)',
        (key, 'conversation', 'public-scope', 'public-topic', 1., 2., 'failed', 'candidate_rejected', created))
    for index, text in enumerate(texts):
        event = key + '-' + str(index)
        pin = worker.digest(text.encode('utf8'))
        db.execute('INSERT INTO bm_task_sources VALUES(?,?,?,?)', (key, event, 1, pin))
        db.execute('INSERT INTO bm_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (event, 'conversation', 'public-scope', 'public-topic', 'user_said', 'valid', 2., 1, pin,
             None, None, 1. + index, None, 'not_applicable', '{}'))
        db.execute('INSERT INTO bm_bodies VALUES(?,?)', (event, text))
    db.commit()


class ContractTests(unittest.TestCase):
    def test_fixed_features_include_unrecognized_diagnostic_family(self):
        value = worker.features('不是未必，没必要，无须否认，不必拒绝，并非不正常。', {}, public.STORE)
        self.assertEqual(1, value['negative_form_counts']['无须'])
        self.assertEqual(1, value['negative_form_counts']['不必'])
        self.assertEqual(1, value['negative_form_counts']['不正常'])
        result = worker.empty_result()
        result['summary'] = value
        worker.validate_output(result)

    def test_latest_complete_nonpolar_group_and_database_unchanged(self):
        with tempfile.TemporaryDirectory(prefix='public-shape-v23-') as directory:
            path = Path(directory).resolve() / 'public.sqlite3'
            with database(path) as db:
                add_task(db, 'eligible', ['不是这一个。', '尚未确认。'], 1)
                add_task(db, 'polar', ['会不会唱歌？'], 6)
                add_task(db, 'missing', ['没有这个。'], 5)
                db.execute("DELETE FROM bm_bodies WHERE event_id='missing-0'")
                add_task(db, 'wrong-scope', ['没有那个。'], 4)
                db.execute("UPDATE bm_events SET scope_id='other' WHERE event_id='wrong-scope-0'")
                add_task(db, 'too-many', ['没有。'] * 3, 3)
            before = path.read_bytes()
            value = worker.select_failed_group(path, public.STORE)
            self.assertEqual(['不是这一个。', '尚未确认。'], [row['text'] for row in value['sources']])
            self.assertEqual(before, path.read_bytes())
            self.assertEqual({'kind': 'conversation', 'id': 'public-scope'}, value['scope'])

    def test_missing_database_not_created_and_no_eligible_model_needed(self):
        with tempfile.TemporaryDirectory(prefix='public-shape-v23-') as directory:
            path = Path(directory).resolve() / 'missing.sqlite3'
            with self.assertRaises(worker.Refused):
                worker.select_failed_group(path, public.STORE)
            self.assertFalse(path.exists())
            with database(path) as db:
                add_task(db, 'question', ['你会不会唱歌？'])
            self.assertIsNone(worker.select_failed_group(path, public.STORE))

    def test_readonly_connection_and_authorizer_reject_mutation(self):
        with tempfile.TemporaryDirectory(prefix='public-shape-v23-') as directory:
            path = Path(directory).resolve() / 'public.sqlite3'
            with database(path) as db:
                add_task(db, 'eligible', ['不是这个。'])
            with contextlib.closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                db.set_authorizer(worker.readonly_authorizer)
                for sql in ('DELETE FROM bm_bodies', 'CREATE TABLE injected(x)', 'PRAGMA user_version=9',
                            "UPDATE bm_bodies SET text='changed'", "INSERT INTO bm_bodies VALUES('x','y')",
                            "ATTACH DATABASE ':memory:' AS injected"):
                    with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                        db.execute(sql)

    def test_exact_audit_devnull_and_single_ro_database(self):
        connections = [0]
        audit = worker.readonly_audit('file:///public.sqlite3?mode=ro', connections)
        holder = types.SimpleNamespace()
        def open_devnull(path, flags):
            self.assertEqual('/dev/null', path)
            audit('open', (path, None, flags))
            return 77
        with patch.object(subprocess.os, 'devnull', '/dev/null'), patch.object(subprocess.os, 'open', open_devnull):
            self.assertEqual(77, subprocess.Popen._get_devnull(holder))
        for path, flags in (('/tmp/forbidden', os.O_WRONLY | os.O_CREAT), ('/dev/video0', os.O_RDONLY)):
            with self.assertRaises(worker.Refused):
                audit('open', (path, None, flags))
        audit('sqlite3.connect', ('file:///public.sqlite3?mode=ro',))
        with self.assertRaises(worker.Refused):
            audit('sqlite3.connect', ('file:///public.sqlite3?mode=ro',))
        with self.assertRaises(worker.Refused):
            worker.readonly_audit('file:///public.sqlite3?mode=ro', [0])('sqlite3.connect', ('file:///public.sqlite3?mode=rw',))

    def prepared(self):
        sources = [dict(event_id='public-event', revision=1, include_in_summary=True,
                        source='user_said', text='尚未确认。', metadata={}, recorded_utc=1.)]
        return dict(schema_version=1, scope=dict(kind='conversation', id='public-scope'), topic='public',
                    start_utc=1., end_utc=2., sources=sources,
                    required_claims=public.STORE.BoardMemoryStore._required_claims(sources))

    def test_actual_client_normal_acceptance_and_rejection_projection(self):
        for answer, accepted in (('尚未确认。', 1), ('已经确认。', 0)):
            inference = public.FakeInference(answer)
            result = worker.diagnose(self.prepared(), public.STORE, public.POLICY, inference,
                                     lambda: None, lambda: False, worker.empty_result())
            self.assertEqual(1, len(inference.calls))
            self.assertEqual(accepted, result['accepted'])
            self.assertEqual(1, result['calls'])
            self.assertIsNotNone(result['summary'])
            worker.validate_output(result)
            if not accepted:
                self.assertIn('negation_missing', result['rejection_reasons'])

    def test_second_model_request_never_occurs_on_reduction(self):
        inference = public.FakeInference('尚未确认。' * 40)
        result = worker.diagnose(self.prepared(), public.STORE, public.POLICY, inference,
                                 lambda: None, lambda: False, worker.empty_result())
        self.assertEqual(1, len(inference.calls))
        self.assertEqual(1, result['calls'])
        self.assertEqual(0, result['accepted'])
        worker.validate_output(result)

    def test_cancel_before_call_and_payload_guard(self):
        inference = public.FakeInference('尚未确认。')
        result = worker.diagnose(self.prepared(), public.STORE, public.POLICY, inference,
                                 lambda: None, lambda: True, worker.empty_result())
        self.assertEqual(0, len(inference.calls))
        self.assertEqual('cancelled', result['code'])

    def test_original_row_state_and_revision_filters(self):
        for column, value in (('revision', 2), ('closed_utc', None), ('state', 'invalid'),
                              ('source', 'assistant_reply'), ('reserved_task', 'other'),
                              ('compacted_summary_id', 'other'), ('body_hash', 'wrong')):
            with self.subTest(column=column), tempfile.TemporaryDirectory(prefix='public-shape-v23-') as directory:
                path = Path(directory).resolve() / 'public.sqlite3'
                with database(path) as db:
                    add_task(db, 'candidate', ['不是这个。'])
                    db.execute('UPDATE bm_events SET ' + column + '=?', (value,))
                self.assertIsNone(worker.select_failed_group(path, public.STORE))
        with tempfile.TemporaryDirectory(prefix='public-shape-v23-') as directory:
            path = Path(directory).resolve() / 'public.sqlite3'
            with database(path) as db:
                add_task(db, 'candidate', ['不是这个。'])
                db.execute("UPDATE bm_bodies SET text='已被更改。'")
            with self.assertRaises(worker.Refused):
                worker.select_failed_group(path, public.STORE)

    def test_guard_failure_has_no_actual_request_and_exception_body_stays_private(self):
        inference = public.FakeInference('尚未确认。')
        guard = lambda: (_ for _ in ()).throw(worker.Refused())
        with self.assertRaises(worker.Refused):
            worker.diagnose(self.prepared(), public.STORE, public.POLICY, inference,
                            guard, lambda: False, worker.empty_result())
        self.assertEqual([], inference.calls)
        class BrokenInference:
            def request(self, *args, **kwargs):
                raise RuntimeError('PRIVATE_SENTINEL_DO_NOT_EXPORT')
            def cancel(self, owner):
                pass
        result = worker.diagnose(self.prepared(), public.STORE, public.POLICY, BrokenInference(),
                                 lambda: None, lambda: False, worker.empty_result())
        self.assertNotIn('PRIVATE_SENTINEL_DO_NOT_EXPORT', json.dumps(worker.validate_output(result)))

    def test_actual_request_deadline_and_duplicate_call_bound(self):
        class DeadlineInference(public.FakeInference):
            def request(inner, kind, payload, *, deadline, cancelled):
                self.assertLessEqual(deadline - time.monotonic(), 30)
                self.assertGreater(deadline - time.monotonic(), 0)
                self.assertLessEqual(payload['budget_ms'], 30000)
                return super(DeadlineInference, inner).request(kind, payload, deadline=deadline, cancelled=cancelled)
        inference = DeadlineInference('尚未确认。')
        worker.diagnose(self.prepared(), public.STORE, public.POLICY, inference,
                        lambda: None, lambda: False, worker.empty_result())
        result = worker.empty_result()
        result['calls'] = 1
        projected = worker.ProjectionClient(inference, public.STORE, public.POLICY,
                                             lambda: None, result, 'private-public-fixture')
        with self.assertRaises(worker.Refused):
            projected.request('llm', {}, deadline=time.monotonic() + 30, cancelled=lambda: False)
        self.assertEqual(1, len(inference.calls))

    def test_parent_rejects_invalid_oversized_and_extra_private_output(self):
        raw_values = [b'PRIVATE_SENTINEL_DO_NOT_EXPORT', b'x' * 32769,
                      json.dumps(dict(worker.empty_result(), raw_text='PRIVATE_SENTINEL_DO_NOT_EXPORT')).encode()]
        for raw in raw_values:
            process = types.SimpleNamespace(returncode=0, communicate=lambda *args, **kwargs: (raw, None), poll=lambda: 0)
            captured = []
            namespace = dict(WORKER_SOURCE=(HERE / 'worker.py').read_text(encoding='utf8'), ARGUMENTS={}, print=captured.append)
            with patch.object(subprocess, 'Popen', return_value=process):
                exec(run_diagnose.REMOTE, namespace)
            value = json.loads(captured[0])
            self.assertEqual('OUTPUT_CONTRACT_REFUSED', value['status'])
            self.assertNotIn('PRIVATE_SENTINEL_DO_NOT_EXPORT', captured[0])

    def test_output_contract_rejects_private_strings_and_keys(self):
        for field in ('code', 'stage', 'error_class'):
            value = worker.empty_result()
            value[field] = 'PRIVATE_SENTINEL_DO_NOT_EXPORT'
            with self.assertRaises(worker.Refused):
                worker.validate_output(value)
        value = worker.empty_result()
        value['raw_response'] = 'PRIVATE_SENTINEL_DO_NOT_EXPORT'
        with self.assertRaises(worker.Refused):
            worker.validate_output(value)
        value = worker.empty_result()
        value['summary'] = worker.features('公开未确认。', {}, public.STORE)
        value['summary']['negative_form_counts']['PRIVATE_SENTINEL_DO_NOT_EXPORT'] = 1
        with self.assertRaises(worker.Refused):
            worker.validate_output(value)

    def test_fd_boundary_suppresses_private_library_output(self):
        script = "import sys;sys.path.insert(0," + repr(str(HERE)) + ");import worker;" \
                 "worker.execute=lambda args:(print('PRIVATE_SENTINEL_DO_NOT_EXPORT'),worker.empty_result())[1];worker.child_main()"
        process = subprocess.run([sys.executable, '-B', '-c', script], input=b'{}', capture_output=True, timeout=5)
        self.assertEqual(0, process.returncode)
        self.assertNotIn(b'PRIVATE_SENTINEL_DO_NOT_EXPORT', process.stdout + process.stderr)
        worker.validate_output(json.loads(process.stdout))

    def test_actual_v23_inputs_dry_and_parent_owns_only_its_child(self):
        common, arguments, source = run_diagnose.inputs()
        self.assertEqual(380, len(arguments['mapping']['component_pins']))
        self.assertEqual(277918, arguments['mapping']['gtk']['pid'])
        self.assertIn('timeout=45', run_diagnose.REMOTE)
        self.assertEqual(2, run_diagnose.REMOTE.count('process.kill()'))
        self.assertNotIn('os.kill', run_diagnose.REMOTE)
        self.assertNotIn('killpg', run_diagnose.REMOTE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
