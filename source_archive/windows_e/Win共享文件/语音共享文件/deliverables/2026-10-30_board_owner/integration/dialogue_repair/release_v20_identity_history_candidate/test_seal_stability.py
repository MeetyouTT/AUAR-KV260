"""Local public receipt fixtures, temporary JSON files and fault injection."""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import seal_stability as seal


class SealStabilityTests(unittest.TestCase):
    def setUp(self):
        self.spec = seal.common.proposed()
        self.spec.update(minor_state='APPLIED', source_manifest_sha256='d' * 64)
        self.ready = dict(status='PRODUCTION_BOARD_BUSINESS_READY', root=self.spec['target'],
            guard_removed=True, data_origin='board', listening_enabled=False, listening_state='PAUSED',
            physical_microphone_opened=False, retention_enabled=True, main_pid=4001, gtk_pid=4002)
        self.installed = dict(status='MINOR_SOURCES_APPLIED_UI_STOPPED', spec=self.spec,
            source_files={name: row['sha256'] for name, row in seal.common.approved_sources().items()},
            production_bootstrap_verified=True, profiles_migration_verified=True,
            gui_configuration_bytes_unchanged=True, private_data_replayed=False,
            new_source_paths=sorted(seal.common.NEW_PATHS))
        self.raws = {name + '.json': seal.common.encoded(value) for name, value in
                     (('spec', self.spec), ('ready', self.ready), ('installed', self.installed))}
        self.products = seal.validate_inputs(self.spec, self.ready, self.installed)
        self.mapping = dict(status='IDENTITY_HISTORY_SOURCE_AND_SERVICE_VERIFIED', observed_mono=1.,
            boot_id=self.spec['boot_id'], root=self.spec['target'], startup_sha256=self.spec['startup_sha256'],
            source_manifest_sha256=self.spec['source_manifest_sha256'],
            configuration_sha256=self.spec['configuration_sha256'],
            component_pins=self.spec['component_sha256'], source_files=self.products,
            supervisor=dict(pid=self.ready['main_pid'], birth_ticks=1, command_sha256='a'*64),
            gtk=dict(pid=self.ready['gtk_pid'], birth_ticks=2, command_sha256='b'*64),
            camera=dict(pid=1335, birth_ticks=2344, command_sha256=self.spec['camera_owner']['camera_cmdline_sha256']),
            current_publication_committed=True, saved_listening_preference=dict(version=1, enabled=False),
            listening=dict(enabled=False, state='PAUSED', microphone_open=False), native_visible=True,
            phase='IDLE', playing=False)

    @contextlib.contextmanager
    def local_paths(self):
        with tempfile.TemporaryDirectory(prefix='public-seal-test-', dir=seal.HERE) as value:
            root = Path(value).resolve()
            assert root.is_relative_to(seal.HERE.resolve())
            canonical = root / 'canonical'
            canonical.mkdir()
            (canonical / 'spec.json').write_bytes((seal.common.PREVIOUS / 'stability_evidence/spec.json').read_bytes())
            (canonical / 'actual_ready.json').write_bytes((seal.common.PREVIOUS / 'stability_evidence/ready.json').read_bytes())
            yield root / 'evidence', canonical

    def test_public_receipt_fixture_has_exact_final_sources_380_pins_and_pause(self):
        self.assertEqual(seal.common.proposed()['startup_sha256'], self.spec['startup_sha256'])
        self.assertEqual(seal.common.ALLOWED_PATHS, set(self.products))
        self.assertIs(self.ready['listening_enabled'], False)
        self.assertEqual(380, len(self.spec['component_sha256']))

    def test_unapplied_spec_or_forged_install_source_rejected(self):
        with self.assertRaises(ValueError):
            seal.validate_inputs(seal.common.proposed(), self.ready, self.installed)
        changed = copy.deepcopy(self.installed)
        changed['source_files'].pop('tools/provisional_voice.py')
        with self.assertRaises(ValueError):
            seal.validate_inputs(self.spec, self.ready, changed)

    def test_ready_with_open_microphone_or_wrong_root_rejected(self):
        for key, value in [('listening_enabled', True), ('physical_microphone_opened', True),
                           ('listening_state', 'WAITING_SPEECH'), ('guard_removed', False),
                           ('root', '/unrelated'), ('main_pid', True)]:
            ready = dict(self.ready)
            ready[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                seal.validate_inputs(self.spec, ready, self.installed)

    def test_mapping_requires_all_pins_and_live_paused_proof(self):
        seal.validate_mapping(self.mapping, self.spec, self.ready, self.products)
        for kind in ('missing_pin', 'wrong_pin', 'enabled', 'zero_bool', 'uncommitted'):
            value = copy.deepcopy(self.mapping)
            if kind == 'missing_pin':
                value['component_pins'].pop('common/board_memory.py')
            elif kind == 'wrong_pin':
                value['component_pins']['common/board_memory.py'] = '0'*64
            elif kind == 'enabled':
                value['listening']['enabled'] = True
            elif kind == 'zero_bool':
                value['saved_listening_preference']['enabled'] = 0
            else:
                value['current_publication_committed'] = False
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                seal.validate_mapping(value, self.spec, self.ready, self.products)

    def test_remote_keeps_source_checks_and_exports_only_numeric_control_metadata(self):
        tree = ast.parse(seal.REMOTE, feature_version=(3, 9))
        self.assertIsInstance(tree, ast.Module)
        for text in ('for rel,pin in pins.items()', "control['phase']=='COMMITTED'",
                     "control['target_startup_sha256']==SPEC['startup_sha256']",
                     "child_fields[1]", "preference['enabled'] is False", "response.read(1048577)",
                     "display.get('visible') is True", "'source_files':PRODUCTS"):
            self.assertIn(text, seal.REMOTE)
        self.assertNotIn('sqlite3', seal.REMOTE)
        self.assertNotIn('write_bytes', seal.REMOTE)

    def test_default_main_does_not_write_or_import_transport(self):
        with self.local_paths() as (evidence, canonical):
            argv = ['seal_stability.py']
            for name in ('spec', 'ready', 'installed'):
                path = canonical.parent / ('public-' + name + '.json')
                raw = self.raws[name + '.json']
                path.write_bytes(raw)
                argv += ['--' + name, str(path), '--' + name + '-sha256', seal.common.sha(raw)]
            with patch('sys.argv', argv), patch.object(seal, 'commit_local', side_effect=AssertionError('write attempted')), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                seal.main()
        self.assertIn('NO_SSH_NO_WRITES', output.getvalue())

    def test_commit_saves_complete_evidence_and_prior_bytes_before_pointers(self):
        with self.local_paths() as (evidence, canonical):
            before = (canonical / 'spec.json').read_bytes()
            result = seal.commit_local(self.raws, self.mapping, evidence=evidence, canonical=canonical)
            self.assertEqual('IDENTITY_HISTORY_EVIDENCE_SEALED_CANONICAL_COMMITTED', result['status'])
            self.assertEqual(before, (evidence / 'previous_canonical_spec.json').read_bytes())
            self.assertEqual(self.raws['spec.json'], (canonical / 'spec.json').read_bytes())
            self.assertEqual(self.raws['ready.json'], (canonical / 'actual_ready.json').read_bytes())
            self.assertEqual('COMMITTED', json.loads((evidence / 'canonical_update_state.json').read_bytes())['phase'])
            self.assertEqual(self.mapping, json.loads((evidence / 'source_mapping.json').read_bytes()))

    def test_partial_pointer_failure_can_retry_with_identical_saved_evidence(self):
        with self.local_paths() as (evidence, canonical):
            original = seal.atomic_file
            def fail_last_pointer(path, raw):
                if path == canonical / 'spec.json':
                    raise OSError('public injected pointer interruption')
                original(path, raw)
            with patch.object(seal, 'atomic_file', side_effect=fail_last_pointer), self.assertRaises(OSError):
                seal.commit_local(self.raws, self.mapping, evidence=evidence, canonical=canonical)
            self.assertEqual('PREPARED', json.loads((evidence / 'canonical_update_state.json').read_bytes())['phase'])
            later = dict(self.mapping, observed_mono=2.)
            seal.commit_local(self.raws, later, evidence=evidence, canonical=canonical)
            self.assertEqual(self.raws['spec.json'], (canonical / 'spec.json').read_bytes())
            self.assertEqual(1., json.loads((evidence / 'source_mapping.json').read_bytes())['observed_mono'])

    def test_foreign_canonical_is_refused_before_evidence_writes(self):
        with self.local_paths() as (evidence, canonical):
            (canonical / 'spec.json').write_bytes(b'public-unrelated-revision')
            with self.assertRaisesRegex(ValueError, 'another_publication'):
                seal.commit_local(self.raws, self.mapping, evidence=evidence, canonical=canonical)
            self.assertFalse(evidence.exists())

    def test_each_actual_receipt_path_and_hash_is_required(self):
        for omitted in ('--spec', '--spec-sha256', '--ready', '--ready-sha256', '--installed', '--installed-sha256'):
            argv = ['seal_stability.py']
            for name in ('spec', 'ready', 'installed'):
                for flag, value in (('--' + name, 'public-' + name + '.json'), ('--' + name + '-sha256', 'a' * 64)):
                    if flag != omitted:
                        argv += [flag, value]
            with self.subTest(omitted=omitted), patch('sys.argv', argv), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                seal.main()

    def test_pending_payload_cannot_execute_seal_transport(self):
        with self.local_paths() as (evidence, canonical):
            argv = ['seal_stability.py', '--execute-root-only']
            for name in ('spec', 'ready', 'installed'):
                path = canonical.parent / ('public-' + name + '.json')
                raw = self.raws[name + '.json']
                path.write_bytes(raw)
                argv += ['--' + name, str(path), '--' + name + '-sha256', seal.common.sha(raw)]
            with patch('sys.argv', argv), patch.object(seal.common, 'PAYLOAD_FINALIZED', False), \
                    self.assertRaisesRegex(ValueError, 'final_source_payload'):
                seal.main()

    def test_added_source_receipt_must_match_the_exact_new_path(self):
        for paths in ([], ['other.py'], ['board/runtime/history_delete.py', 'other.py']):
            changed = dict(self.installed, new_source_paths=paths)
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                seal.validate_inputs(self.spec, self.ready, changed)

    def test_canonical_changed_during_evidence_writes_is_not_overwritten(self):
        with self.local_paths() as (evidence, canonical):
            original = seal.exact_file
            old_ready = (canonical / 'actual_ready.json').read_bytes()
            def changed_after_proof(path, raw):
                original(path, raw)
                if path.name == 'previous_canonical_spec.json':
                    (canonical / 'spec.json').write_bytes(b'public-other-release')
            with patch.object(seal, 'exact_file', changed_after_proof), self.assertRaisesRegex(ValueError, 'during_evidence'):
                seal.commit_local(self.raws, self.mapping, evidence=evidence, canonical=canonical)
            self.assertEqual((canonical / 'spec.json').read_bytes(), b'public-other-release')
            self.assertEqual((canonical / 'actual_ready.json').read_bytes(), old_ready)


if __name__ == '__main__':
    unittest.main()
