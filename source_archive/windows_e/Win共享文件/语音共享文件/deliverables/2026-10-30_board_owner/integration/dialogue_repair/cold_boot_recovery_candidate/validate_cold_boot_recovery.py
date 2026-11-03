"""Standalone public SQLite crash tests. No production database is opened.

Linux execution verifies every supplied runtime component pin before importing
the three candidate modules. Temporary databases live only in /dev/shm.
Windows local checks use kernel byte locks in place of POSIX flock and retain
real SQLite child crashes, journals, rollback and SQL lock conflicts.
"""
import argparse
from contextlib import closing
import hashlib
import importlib.util
import io
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


HERE = Path(__file__).resolve().parent
SOURCE_NAMES = (
    'common/board_production_bootstrap.py',
    'board/runtime/board_business.py',
    'tools/production_board_business_gui.py',
)
BOOT = 'public-cold-boot-recovery-test'
IMPORT_REPORT = dict(profiles=0, issued_profile_grants=0)
CRASH_SOURCE = """
import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1], isolation_level=None)
db.execute('PRAGMA cache_size=5')
db.execute('PRAGMA synchronous=FULL')
db.execute('BEGIN IMMEDIATE')
db.execute("UPDATE payload SET value=zeroblob(8192)")
db.execute("UPDATE bm_production_origin SET database_uuid='uncommitted-change'")
os._exit(73)
"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_sources(runtime_root, mapping_path, local_source_only):
    runtime_root = runtime_root.resolve(strict=True)
    mapping = json.loads(mapping_path.read_text(encoding='utf-8-sig'))
    pins = mapping['component_pins']
    manifest = json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    verified = 0
    for relative, fingerprint in pins.items():
        if local_source_only and relative not in SOURCE_NAMES:
            continue
        path = runtime_root/relative
        if path.resolve(strict=True) != path or sha(path) != fingerprint:
            raise RuntimeError('Runtime source mismatch ' + relative)
        verified += 1
    if not local_source_only and verified != len(pins):
        raise RuntimeError('Incomplete runtime pin check')
    for relative in SOURCE_NAMES:
        item = manifest['sources'][relative]
        if item['before_sha256'] != pins[relative]:
            raise RuntimeError('Candidate base differs from runtime ' + relative)
        if sha(HERE/'before'/relative) != item['before_sha256']:
            raise RuntimeError('Candidate baseline changed ' + relative)
        if sha(HERE/'after'/relative) != item['after_sha256']:
            raise RuntimeError('Candidate source changed ' + relative)
    return dict(runtime_components_verified=verified,
                runtime_component_total=len(pins),
                complete_runtime_mapping_verified=not local_source_only,
                candidate_sources_verified=len(SOURCE_NAMES),
                source_mapping_sha256=sha(mapping_path),
                source_manifest_sha256=sha(HERE/'SOURCE_MANIFEST.json'))


class WindowsTestWriterLease:
    """Actual local kernel lock for Windows tests of constructor ordering."""
    filename = 'writer.lock'

    def __init__(self, root, boot_id=None, *, data_origin=None):
        import msvcrt
        self.root = Path(root).resolve(strict=True)
        self.fd = None
        fd = os.open(str(self.root/self.filename), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if not os.fstat(fd).st_size:
                os.write(fd, b'0')
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            self.fd = fd
        except BaseException:
            os.close(fd)
            raise

    def close(self):
        import msvcrt
        if self.fd is not None:
            fd, self.fd = self.fd, None
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            finally:
                os.close(fd)


class WindowsTestSpeakerLease(WindowsTestWriterLease):
    filename = 'speaker-writer.lock'


def windows_private_root(value):
    root = Path(value).absolute()
    if root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('Invalid public fixture root')
    return root


def windows_private_file(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid public fixture relative path')
    path = root/relative
    if path.resolve(strict=True) != path or root not in path.parents or not path.is_file():
        raise ValueError('Invalid public fixture file')
    return path


class PublicFixture:
    def __init__(self, bootstrap):
        temp_root = Path('/dev/shm') if os.name == 'posix' else Path(tempfile.gettempdir())
        self.temp_root = temp_root.resolve(strict=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='aura-cold-boot-public-', dir=str(temp_root))
        self.root = Path(self.temporary.name).resolve(strict=True)
        assert self.root.parent == self.temp_root
        assert self.root.name.startswith('aura-cold-boot-public-')
        self.root.chmod(0o700)
        (self.root/'speaker').mkdir(mode=0o700)
        bundle = '1'*32
        targets = {}
        self.origins = {}
        for index, (kind, relative) in enumerate(bootstrap.TARGETS.items()):
            path = self.root/relative
            db = sqlite3.connect(str(path), isolation_level=None)
            try:
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute('PRAGMA synchronous=FULL')
                db.execute('PRAGMA application_id='+str(bootstrap.APPLICATION_IDS[kind]))
                db.execute(bootstrap.ORIGIN_DDL)
                origin = dict(slot=1, database_uuid=str(index+1)*32, bundle_id=bundle,
                              sources_sha256='2'*64, migration_manifest_sha256='3'*64)
                self.origins[kind] = origin
                db.execute('INSERT INTO bm_production_origin VALUES(?,?,?,?,?)', tuple(origin.values()))
                db.execute('CREATE TABLE payload(id INTEGER PRIMARY KEY, value BLOB NOT NULL)')
                db.execute('BEGIN IMMEDIATE')
                db.executemany('INSERT INTO payload VALUES(?,?)',
                               ((i, b'committed-'+bytes([65+index])*8182) for i in range(128)))
                db.commit()
                if kind == 'timeline':
                    db.execute('CREATE TABLE bm_meta(key TEXT PRIMARY KEY, value TEXT)')
                    db.execute("INSERT INTO bm_meta VALUES('data_origin','board')")
                    for table in ('bm_migrations', 'bm_observation_migrations'):
                        db.execute('CREATE TABLE '+table+'(import_id TEXT PRIMARY KEY, state TEXT, source_sha256 TEXT, report TEXT)')
                        db.execute('INSERT INTO '+table+' VALUES(?,?,?,?)',
                                   (table, 'complete', '4'*64, json.dumps(IMPORT_REPORT)))
                    db.execute('CREATE TABLE bm_scopes(kind TEXT, id TEXT)')
                db.row_factory = sqlite3.Row
                targets[kind] = dict(path=relative, database_uuid=origin['database_uuid'],
                    sources_sha256=origin['sources_sha256'],
                    migration_manifest_sha256=origin['migration_manifest_sha256'],
                    user_version=0, schema_sha256=bootstrap._schema_hash(db, kind))
            finally:
                db.close()
            path.chmod(0o600)
        key = self.root/'speaker/identity-link-receipt.key'
        key.write_bytes(bytes(range(32)))
        assert key.stat().st_size == 32
        model = 'public-synthetic-speaker-model'
        for relative, value in (
                ('speaker/speaker-business-owner.json', dict(data_origin='board', origin='imported_snapshot', model_id=model)),
                ('speaker/speaker-gallery-namespace.json', dict(version=1, model_id=model))):
            (self.root/relative).write_text(json.dumps(value), encoding='utf-8')
        receipt = dict(schema=bootstrap.SCHEMA, bundle_id=bundle, data_origin='board',
            private_root=str(self.root), initial_retention_enabled=False, targets=targets,
            imports=dict(conversation=dict(import_id='bm_migrations', source_sha256='4'*64),
                         observation=dict(import_id='bm_observation_migrations', source_sha256='4'*64)),
            profiles_migration_verified=True, profiles_imported=0, speaker_model_id=model,
            speaker_receipt_key_sha256=sha(key), conversation_selection_verified=False,
            conversation_selection_sha256=None)
        self.receipt = self.root/'production-bootstrap.json'
        self.receipt.write_text(json.dumps(receipt), encoding='utf-8')
        for path in (key, self.receipt, self.root/'speaker/speaker-business-owner.json',
                     self.root/'speaker/speaker-gallery-namespace.json'):
            path.chmod(0o600)
        self.receipt_sha256 = sha(self.receipt)
        self.timeline = self.root/'timeline.sqlite3'

    def crash(self, kind='timeline'):
        path = self.root/BOOTSTRAP.TARGETS[kind]
        result = subprocess.run([sys.executable, '-B', '-c', CRASH_SOURCE, str(path)],
                                capture_output=True, text=True, timeout=15)
        if result.returncode != 73:
            raise AssertionError('Public crash child failed '+result.stderr)
        journal = Path(str(path)+'-journal')
        assert journal.is_file() and journal.stat().st_size > 512
        if os.name == 'posix':
            journal.chmod(0o600)
        return journal

    def close(self):
        # Only this freshly created public fixture directory can be removed.
        assert self.root.resolve(strict=True).parent == self.temp_root
        assert self.root.name.startswith('aura-cold-boot-public-')
        self.temporary.cleanup()


class PublicRuntime:
    def __init__(self, config, boot_id, *, writer_lock, bootstrap_proof, **kwargs):
        self.writer_lock = writer_lock
        self.bootstrap_proof = bootstrap_proof
        if writer_lock.fd is None or bootstrap_proof.get('receipt_verified') is not True:
            raise AssertionError('Runtime construction before complete verification')

    def close(self):
        self.writer_lock.close()


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.patches = []
        if os.name != 'posix':
            for item in (
                    patch.object(BOOTSTRAP, '_private_root', windows_private_root),
                    patch.object(BOOTSTRAP, '_private_file', windows_private_file),
                    patch.object(BUSINESS, '_BoardWriterLock', WindowsTestWriterLease),
                    patch.object(SPEAKER, '_WriterLease', WindowsTestSpeakerLease)):
                item.start()
                self.patches.append(item)
                self.addCleanup(item.stop)
        self.fixture = PublicFixture(BOOTSTRAP)
        self.addCleanup(self.fixture.close)
        self.config = types.SimpleNamespace(data_origin='board', private_root=str(self.fixture.root),
            bootstrap_receipt=str(self.fixture.receipt), bootstrap_receipt_sha256=self.fixture.receipt_sha256)
        BOOTSTRAP.verify_production_bootstrap(self.fixture.root, self.fixture.receipt, self.fixture.receipt_sha256)

    def construct(self):
        with patch.object(BUSINESS, 'BoardBusinessRuntime', PublicRuntime):
            return BUSINESS.create_board_business_runtime(self.config, BOOT)

    def assert_committed_content(self, kind='timeline'):
        path = self.fixture.root/BOOTSTRAP.TARGETS[kind]
        with closing(sqlite3.connect(str(path))) as db:
            db.row_factory = sqlite3.Row
            self.assertEqual(dict(db.execute('SELECT * FROM bm_production_origin').fetchone()),
                             self.fixture.origins[kind])
            values = [row[0] for row in db.execute('SELECT value FROM payload')]
            self.assertEqual(len(values), 128)
            self.assertTrue(all(value.startswith(b'committed-') for value in values))
            self.assertEqual(db.execute('PRAGMA quick_check').fetchone()[0], 'ok')

    def assert_locks_released(self):
        board = BUSINESS._BoardWriterLock(self.fixture.root, BOOT)
        try:
            speaker = SPEAKER._WriterLease(self.fixture.root/'speaker', data_origin='board')
            speaker.close()
        finally:
            board.close()

    def test_hot_journal_readonly_fails_and_normal_factory_recovers(self):
        journal = self.fixture.crash()
        before = sha(journal)
        with self.assertRaises(sqlite3.OperationalError) as error:
            BOOTSTRAP.verify_production_bootstrap(self.fixture.root, self.fixture.receipt, self.fixture.receipt_sha256)
        self.assertTrue('readonly' in str(error.exception).lower())
        self.assertEqual(sha(journal), before)
        preflight = BOOTSTRAP.verify_production_bootstrap_receipt(
            self.fixture.root, self.fixture.receipt, self.fixture.receipt_sha256)
        self.assertFalse(preflight['database_contents_verified'])
        self.assertEqual(sha(journal), before)
        runtime = self.construct()
        try:
            self.assertTrue(runtime.bootstrap_proof['receipt_verified'])
            self.assertFalse(journal.exists())
            self.assert_committed_content()
            self.assertEqual(sha(self.fixture.receipt), self.fixture.receipt_sha256)
            with self.assertRaises((OSError, RuntimeError)):
                BUSINESS._BoardWriterLock(self.fixture.root, BOOT)
            speaker = SPEAKER._WriterLease(self.fixture.root/'speaker', data_origin='board')
            speaker.close()
        finally:
            runtime.close()
        self.assert_locks_released()

    def test_all_four_target_journals_recover_under_same_leases(self):
        journals = [self.fixture.crash(kind) for kind in BOOTSTRAP.TARGETS]
        runtime = self.construct()
        try:
            for kind in BOOTSTRAP.TARGETS:
                self.assert_committed_content(kind)
            self.assertTrue(all(not path.exists() for path in journals))
        finally:
            runtime.close()

    def test_bad_receipt_fingerprint_opens_no_sql_and_keeps_journal(self):
        journal = self.fixture.crash()
        before = sha(journal)
        self.config.bootstrap_receipt_sha256 = 'f'*64
        with patch.object(BOOTSTRAP.sqlite3, 'connect', side_effect=AssertionError('SQL opened before receipt check')):
            with self.assertRaises(BOOTSTRAP.ProductionBootstrapRejected):
                self.construct()
        self.assertEqual(sha(journal), before)
        self.assertFalse((self.fixture.root/'writer.lock').exists())

    def test_missing_database_is_rejected_without_recreation(self):
        missing = self.fixture.root/'speaker/speakers.sqlite3'
        self.assertEqual(missing.resolve().parent, self.fixture.root/'speaker')
        missing.unlink()
        with self.assertRaises(FileNotFoundError):
            self.construct()
        self.assertFalse(missing.exists())
        self.assertFalse((self.fixture.root/'writer.lock').exists())

    def test_committed_origin_tampering_still_rejected_after_recovery(self):
        with closing(sqlite3.connect(str(self.fixture.timeline))) as db:
            db.execute("UPDATE bm_production_origin SET bundle_id=?", ('e'*32,))
            db.commit()
        journal = self.fixture.crash()
        with self.assertRaises(BOOTSTRAP.ProductionBootstrapRejected) as error:
            self.construct()
        self.assertEqual(str(error.exception), 'target_origin_or_schema_changed')
        self.assertFalse(journal.exists())
        with closing(sqlite3.connect(str(self.fixture.timeline))) as db:
            self.assertEqual(db.execute('SELECT bundle_id FROM bm_production_origin').fetchone()[0], 'e'*32)
        self.assert_locks_released()

    def test_board_writer_conflict_rejects_before_recovery(self):
        journal = self.fixture.crash()
        before = sha(journal)
        lease = BUSINESS._BoardWriterLock(self.fixture.root, BOOT)
        try:
            with self.assertRaises((OSError, RuntimeError)):
                self.construct()
            self.assertEqual(sha(journal), before)
        finally:
            lease.close()
        self.assert_locks_released()

    def test_speaker_writer_conflict_releases_board_lease(self):
        journal = self.fixture.crash()
        before = sha(journal)
        lease = SPEAKER._WriterLease(self.fixture.root/'speaker', data_origin='board')
        try:
            with self.assertRaises((OSError, RuntimeError)):
                self.construct()
            self.assertEqual(sha(journal), before)
            board = BUSINESS._BoardWriterLock(self.fixture.root, BOOT)
            board.close()
        finally:
            lease.close()
        self.assert_locks_released()

    def test_sqlite_exclusive_lock_is_bounded_and_does_not_construct_runtime(self):
        db = sqlite3.connect(str(self.fixture.timeline), isolation_level=None)
        db.execute('BEGIN EXCLUSIVE')
        try:
            began = time.monotonic()
            with self.assertRaises(sqlite3.OperationalError) as error:
                self.construct()
            self.assertIn('locked', str(error.exception).lower())
            self.assertLess(time.monotonic()-began, 2)
        finally:
            db.rollback()
            db.close()
        self.assert_locks_released()
        self.assert_committed_content()

    def test_recovery_rejects_foreign_or_closed_leases(self):
        journal = self.fixture.crash()
        before = sha(journal)
        with self.assertRaises(BOOTSTRAP.ProductionBootstrapRejected):
            BOOTSTRAP.verify_production_bootstrap(self.fixture.root, self.fixture.receipt,
                self.fixture.receipt_sha256, recovery_leases=(object(), object()))
        board = BUSINESS._BoardWriterLock(self.fixture.root, BOOT)
        speaker = SPEAKER._WriterLease(self.fixture.root/'speaker', data_origin='board')
        board.close()
        try:
            with self.assertRaises(BOOTSTRAP.ProductionBootstrapRejected):
                BOOTSTRAP.verify_production_bootstrap(self.fixture.root, self.fixture.receipt,
                    self.fixture.receipt_sha256, recovery_leases=(board, speaker))
        finally:
            speaker.close()
        self.assertEqual(sha(journal), before)

    def test_recovery_connection_rejects_application_sql_writes(self):
        db = BOOTSTRAP._db(self.fixture.timeline, recover=True)
        try:
            with self.assertRaises(sqlite3.OperationalError) as error:
                db.execute('DELETE FROM payload')
            self.assertIn('readonly', str(error.exception).lower())
        finally:
            db.close()
        self.assert_committed_content()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--source-mapping', type=Path, required=True)
    parser.add_argument('--local-source-only', action='store_true')
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    if args.local_source_only and os.name == 'posix':
        parser.error('Linux requires the complete supplied runtime mapping')
    sources = validate_sources(args.runtime_root, args.source_mapping, args.local_source_only)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_SOURCE_VALIDATED', **sources)))
        return 0
    sys.path.insert(0, str(args.runtime_root.resolve(strict=True)))
    global BOOTSTRAP, BUSINESS, SPEAKER
    BOOTSTRAP = load_module('common.board_production_bootstrap', HERE/'after'/SOURCE_NAMES[0])
    BUSINESS = load_module('board.runtime.board_business', HERE/'after'/SOURCE_NAMES[1])
    from board.runtime import board_speaker_business
    SPEAKER = board_speaker_business
    text = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryTests)
    result = unittest.TextTestRunner(stream=text, verbosity=2).run(suite)
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL',
        schema='aura.public-cold-boot-recovery-tests.v1',
        platform=os.name, sqlite_version=sqlite3.sqlite_version,
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        true_posix_writer_leases_tested=os.name == 'posix',
        windows_kernel_lock_substitution=os.name != 'posix',
        real_sqlite_crash_subprocesses=True,
        production_database_or_model_opened=False,
        temporary_database_parent='/dev/shm' if os.name == 'posix' else tempfile.gettempdir(),
        results=text.getvalue(), **sources)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
