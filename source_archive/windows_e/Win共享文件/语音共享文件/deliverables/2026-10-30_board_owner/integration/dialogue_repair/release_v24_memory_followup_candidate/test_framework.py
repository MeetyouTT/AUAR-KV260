"""Public local v24 transport tests. No device, model or production database calls."""
import ast
import base64
import contextlib
import copy
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import apply_followup_closed
import followup_common as common
import seal_followup
from rollforward import roll_forward


@contextlib.contextmanager
def public_selection(relative=common.POLICY_RELATIVE):
    """Only an in-memory test selection, with execution left disabled."""
    source = common.original_policy() + b'\n# PUBLIC TRANSPORT FIXTURE ONLY\n'
    selected = {'baseline_spec_sha256': common.BASE_SPEC_SHA, 'sources': {
        relative: {'before_sha256': common.OLD_SOURCE_PINS[relative], 'sha256': common.sha(source),
            'local_source': 'PUBLIC_IN_MEMORY.py'}}, 'decision': {}}
    decision = {'reviewer': 'root_assistant', 'selected_sources': selected['sources'],
        'bounded_change': {'product_sources': 1, 'other_components': 379,
            'schema_permissions_commit_cleanup_and_deadline_ast_preserved': True},
        'scope': 'PUBLIC_TEST_FIXTURE_NOT_A_REAL_PRODUCT_SELECTION'}
    decision_raw = common.encoded(decision)
    selected['decision'] = {'path': 'PUBLIC_DECISION.json', 'sha256': common.sha(decision_raw)}
    raw = common.encoded(selected)
    expected = common.sha(raw)
    previous = common.pinned

    def pinned(path, digest):
        values = {str(common.HERE / 'APPROVED_PAYLOAD.json'): raw,
            'PUBLIC_IN_MEMORY.py': source, 'PUBLIC_DECISION.json': decision_raw}
        if str(path) in values:
            value = values[str(path)]
            common.need(common.sha(value) == digest, 'public_fixture_hash_changed')
            return value
        return previous(path, digest)

    with patch.object(common, 'APPROVED_PAYLOAD_SHA', expected), patch.object(common, 'pinned', pinned):
        yield selected


def previous_fixture():
    folder = common.v23.PREVIOUS
    old_path = list(sys.path)
    sys.path.insert(0, str(folder))
    try:
        module = common.load_pinned_module('_v22_public_fixture_for_v24', folder / 'test_rebind.py',
            'eeb48cad14432b5b4a2411f93888fe901011312de5027d00d4d34b9e36015218')
        return module.PublicApplyFixture
    finally:
        sys.path[:] = old_path


class PublicFollowupFixture(previous_fixture()):
    def __init__(self, directory):
        super().__init__(directory)
        relative = common.POLICY_RELATIVE
        self.source_paths = [relative]
        self.gui_raw = common.encoded(self.base_gui)
        self.stage = self.control / 'memory-followup-v24-public'
        self.new_raws = {relative: b'PUBLIC_VALUE=2\n'}
        self.base_pins.pop('public/component_0.py')
        self.base_pins[relative] = common.sha(b'PUBLIC_VALUE=1\n')
        self.base_startup = {'runtime': str(self.root / 'runtime'), 'component_sha256': self.base_pins}
        self.old_manifest.update(component_pins=self.base_pins)
        self.targets = [self.root / 'runtime/aura' / relative,
            self.root / 'startup/config.json', self.root / 'production_source_manifest.json']
        for path, raw in zip(self.targets, [b'PUBLIC_VALUE=1\n', common.encoded(self.base_startup), common.encoded(self.old_manifest)]):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.old = [path.read_bytes() for path in self.targets]
        self.new_pins = dict(self.base_pins)
        self.new_pins[relative] = common.sha(self.new_raws[relative])
        self.sources = {relative: {'before_sha256': self.base_pins[relative], 'sha256': self.new_pins[relative],
            'local_source': 'PUBLIC_LOCAL_ONLY'}}
        self.new_startup = dict(self.base_startup, component_sha256=self.new_pins)
        camera_stage = self.control / 'prior-camera-rebind'
        camera_stage.mkdir()
        camera_tx = common.encoded({'applied_spec_sha256': common.CAMERA_SPEC_SHA})
        (camera_stage / 'transaction.json').write_bytes(camera_tx)
        summary_stage = self.control / 'prior-summary-v23'
        summary_stage.mkdir()
        summary_tx = common.encoded({'applied_spec_sha256': common.BASE_SPEC_SHA})
        (summary_stage / 'transaction.json').write_bytes(summary_tx)
        old_sources = {relative: {'sha256': pin} for relative, pin in common.OLD_SOURCE_PINS.items()}
        self.proposed = dict(target=str(self.root), boot_id='PUBLIC_BOOT', component_sha256=self.new_pins,
            configuration_sha256=common.sha(self.gui_raw), startup_sha256=common.sha(common.encoded(self.new_startup)),
            source_manifest_sha256='0' * 64, minor_prepared_configuration_path=str(self.external),
            camera_owner={'camera_pid': 229296}, camera_rebind={'stage': str(camera_stage)},
            summary_revision={'state': 'APPLIED', 'stage': str(summary_stage), 'payload': {'sources': old_sources}},
            summary_followup={'stage': str(self.stage), 'state': 'PROPOSED', 'payload': {'sources': self.sources}})
        self.initial_journal['camera_rebind'] = dict(state='APPLIED', stage=str(camera_stage), transaction_sha256=common.sha(camera_tx))
        self.initial_journal['summary_revision'] = dict(state='APPLIED', stage=str(summary_stage),
            payload_sha256=common.sha(common.encoded(common.OLD_SOURCE_PINS)), transaction_sha256=common.sha(summary_tx))
        self.state_path.write_bytes(common.encoded(self.initial_journal))

    def atomic(self, path, raw):
        Path(path).write_bytes(raw)
        if Path(path) in self.targets:
            self.checkpoint('replace:' + ('source', 'startup', 'manifest')[self.targets.index(Path(path))])

    def invoke(self):
        self.lease_count = 0
        fake_os = types.SimpleNamespace(**{key: getattr(os, key) for key in ('open', 'fdopen', 'fsync', 'close', 'O_RDWR', 'O_RDONLY')})
        fake_os.O_NOFOLLOW = getattr(os, 'O_NOFOLLOW', 0)
        fake_os.O_DIRECTORY = getattr(os, 'O_DIRECTORY', 0)
        fake_os.geteuid = getattr(os, 'geteuid', lambda: self.control.stat().st_uid)

        def flock(*unused):
            self.lease_count += 1

        adapter = types.SimpleNamespace(read=self.read, parse=json.loads, encoded=common.encoded, sha=common.sha,
            create=self.create, relative=lambda value: value, show=lambda: {'ActiveState': 'inactive'})
        namespace = dict(Path=self.path, os=fake_os, c=adapter, sys=sys,
            fcntl=types.SimpleNamespace(flock=flock, LOCK_EX=1, LOCK_NB=2),
            boot=self.guard, journal=self.journal, inactive=self.guard, ownerless=self.guard,
            guarded=self.guard, reviewed_face=self.guard, source=self.guard, need=common.need,
            save=self.save, atomic=self.atomic, SPEC=copy.deepcopy(self.proposed),
            CONTROL=self.control, STATE=self.state_path, EXACT_TARGET=str(self.root), REVISION=common.REVISION,
            BASE_PINS=self.base_pins, BASE_STARTUP=self.base_startup, BASE_CONFIG_SHA=common.sha(self.gui_raw),
            BASE_STARTUP_SHA=common.sha(self.old[1]), BASE_MANIFEST_SHA=common.sha(self.old[2]),
            BASE_SPEC_SHA=common.BASE_SPEC_SHA, CAMERA_SPEC_SHA=common.CAMERA_SPEC_SHA,
            BASE_SOURCE_PINS={relative: self.base_pins[relative] for relative in self.source_paths},
            SOURCE_PATHS=self.source_paths, CONFIGURATION_PATH=str(self.external),
            LAUNCHER_SHA=common.sha(b'PUBLIC_LAUNCHER'), EXPECTED_GUI=self.base_gui, EXPECTED_STARTUP=self.new_startup,
            PAYLOAD={relative: dict(row, base64=base64.b64encode(self.new_raws[relative]).decode())
                for relative, row in self.sources.items()})
        exec(compile(apply_followup_closed.original_transaction_helpers(), '<public-pinned-helper>', 'exec'), namespace)
        tree = ast.parse((common.HERE / 'apply_runtime.py').read_bytes())
        definitions = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<public-exact-followup-apply>', 'exec'), namespace)
        namespace['fsync_directory'] = lambda path: self.checkpoint('fsync:' + Path(path).name)
        if os.name == 'nt':
            def windows_private_directory(path):
                path = Path(path)
                path.mkdir(exist_ok=True)
                common.need(path.resolve() == path and not path.is_symlink(), 'public_directory_redirected')
            namespace['private_directory'] = windows_private_directory
        module = types.ModuleType('common.board_production_bootstrap')
        module.verify_production_bootstrap = self.bootstrap
        package = types.ModuleType('common')
        package.__path__ = []
        with patch.dict(sys.modules, {'common': package, 'common.board_production_bootstrap': module}):
            return namespace['apply_followup']()


class SourceClosureTests(unittest.TestCase):
    def test_draft_cannot_propose_or_execute(self):
        with patch.object(common, 'PAYLOAD_FINALIZED', False), patch.object(common, 'APPROVED_PAYLOAD_SHA', None):
            with self.assertRaisesRegex(ValueError, 'selection_pending'):
                common.proposed()
            with self.assertRaisesRegex(ValueError, 'final_root_selected'):
                common.execute_remote('', {})

    def test_actual_committed_v23_baseline_and_current_canonical(self):
        base = common.baseline()
        common.require_current_baseline()
        self.assertEqual(common.BASE_STARTUP_SHA, base['startup_sha256'])
        self.assertEqual(380, len(base['component_sha256']))
        self.assertEqual(common.v23.publisher_remote(base), common.publisher_remote(base))

    def test_single_policy_keeps_old_transactions_config_and_other379(self):
        with public_selection():
            base, proposed = common.baseline(), common.proposed()
            self.assertEqual({common.POLICY_RELATIVE}, {name for name in base['component_sha256'] if base['component_sha256'][name] != proposed['component_sha256'][name]})
            for field in ('camera_rebind', 'summary_revision', 'configuration_sha256', 'face_readback', 'camera_owner', 'expected_final_listening_enabled'):
                self.assertEqual(base[field], proposed[field])
            self.assertEqual(common.OLD_SOURCE_PINS['common/board_memory.py'], proposed['component_sha256']['common/board_memory.py'])
            for source in (common.publisher_remote(proposed), apply_followup_closed.build_remote(proposed), seal_followup.build_remote(proposed)):
                ast.parse(source, feature_version=(3, 9))

    def test_core_source_is_no_longer_an_allowed_selection(self):
        with public_selection('common/board_memory.py'), self.assertRaisesRegex(ValueError, 'only_summary_policy'):
            common.proposed()

    def test_only_messages_body_normalizes_to_actual_v23_module(self):
        original = common.original_policy()
        tree = ast.parse(original)
        client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardSummaryClient')
        method = next(node for node in client.body if isinstance(node, ast.FunctionDef) and node.name == '_messages')
        method.body.insert(0, ast.parse("public_prompt_marker = 'public only'").body[0])
        self.assertEqual(common.protected_source_ast(original), common.protected_source_ast(ast.unparse(tree)))

    def test_other_methods_imports_budget_and_messages_signature_are_protected(self):
        original = common.original_policy()
        for boundary in ('fragments', 'infer', 'constructor', 'signature', 'decorator', 'module', 'import'):
            tree = ast.parse(original)
            client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardSummaryClient')
            methods = {node.name: node for node in client.body if isinstance(node, ast.FunctionDef)}
            if boundary in ('fragments', 'infer', 'constructor'):
                name = {'fragments': '_fragments', 'infer': '_infer', 'constructor': '__init__'}[boundary]
                methods[name].body.append(ast.Pass())
            elif boundary == 'signature':
                methods['_messages'].args.defaults = [ast.Constant(value=True)]
            elif boundary == 'decorator':
                methods['_messages'].decorator_list.append(ast.Name(id='staticmethod', ctx=ast.Load()))
            elif boundary == 'module':
                tree.body.append(ast.parse('PUBLIC_UNRELATED_VALUE = 1').body[0])
            else:
                tree.body.insert(0, ast.Import(names=[ast.alias(name='inspect')]))
            with self.subTest(boundary=boundary):
                self.assertNotEqual(common.protected_source_ast(original), common.protected_source_ast(ast.unparse(tree)))

    def test_lifecycle_functions_unchanged_and_three_proof_anchors_present(self):
        with public_selection():
            old = common.publisher_remote(common.baseline())
            new = common.publisher_remote(common.proposed())
            functions = lambda source: {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
            self.assertEqual(functions(old), functions(new))
            self.assertIn(repr(common.CAMERA_SPEC_SHA), new)
            self.assertIn(repr(common.BASE_SPEC_SHA), new)
            self.assertIn("followup_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC))", new)

    def test_changed_prior_transaction_or_config_or_pause_refuses(self):
        with public_selection():
            for key in ('camera_rebind', 'summary_revision', 'configuration_sha256', 'expected_final_listening_enabled'):
                spec = common.proposed()
                spec[key] = 'FOREIGN_PUBLIC_VALUE'
                with self.subTest(key=key), self.assertRaises(ValueError):
                    common.validate_spec(spec, allow_proposed=True)


class RollForwardTests(unittest.TestCase):
    def test_all_eight_mixed_states_finish_only_forward(self):
        paths = ['source', 'startup', 'manifest']
        old = {path: ('old-' + path).encode() for path in paths}
        new = {path: ('new-' + path).encode() for path in paths}
        for bits in itertools.product((False, True), repeat=3):
            values = {path: new[path] if bit else old[path] for path, bit in zip(paths, bits)}
            roll_forward(paths, {path: common.sha(raw) for path, raw in old.items()}, new,
                read=values.__getitem__, replace=values.__setitem__, guard=lambda: None)
            self.assertEqual(new, values)

    def test_foreign_bytes_block_every_write(self):
        values = dict(source=b'FOREIGN', startup=b'old', manifest=b'old')
        with self.assertRaises(ValueError):
            roll_forward(list(values), {path: common.sha(b'old') for path in values}, {path: b'new' for path in values},
                read=values.__getitem__, replace=lambda *args: self.fail('Unexpected write'), guard=lambda: None)


class ActualApplyFunctionTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix='public-memory-v24-')
        self.addCleanup(directory.cleanup)
        return PublicFollowupFixture(directory.name)

    def test_complete_and_result_lost_retry_preserve_both_prior_transactions(self):
        fixture = self.fixture()
        result = fixture.invoke()
        self.assertEqual('SUMMARY_FOLLOWUP_SOURCE_APPLIED_UI_STOPPED', result['status'])
        self.assertEqual((1, 379), (result['changed_component_count'], result['unchanged_component_count']))
        self.assertEqual(result, fixture.invoke())
        for key in ('camera_rebind', 'summary_revision'):
            self.assertEqual(fixture.initial_journal[key], fixture.journal()[key])
        self.assertEqual(fixture.gui_raw, fixture.external.read_bytes())

    def test_nine_interruptions_recover_before_after_each_target_and_commit(self):
        points = ['create:memory-source.py', 'create:prepared-memory-source.py', 'create:transaction.json',
            'fsync:before', 'journal:SUMMARY_FOLLOWUP_INTENT', 'replace:source', 'replace:startup',
            'replace:manifest', 'journal:NORMAL_CLOSED']
        for point in points:
            with self.subTest(point=point):
                fixture = self.fixture()
                fixture.fail_at = point
                with self.assertRaisesRegex(RuntimeError, 'PUBLIC_INJECTED_INTERRUPTION'):
                    fixture.invoke()
                self.assertEqual('SUMMARY_FOLLOWUP_SOURCE_APPLIED_UI_STOPPED', fixture.invoke()['status'])
                self.assertEqual(fixture.gui_raw, fixture.external.read_bytes())

    def test_all_eight_owned_intent_mixtures(self):
        for bits in itertools.product((False, True), repeat=3):
            with self.subTest(bits=bits):
                fixture = self.fixture()
                fixture.fail_at = 'replace:manifest'
                with self.assertRaises(RuntimeError):
                    fixture.invoke()
                expected = [path.read_bytes() for path in fixture.targets]
                for path, bit, before, after in zip(fixture.targets, bits, fixture.old, expected):
                    path.write_bytes(after if bit else before)
                fixture.invoke()
                self.assertEqual(expected, [path.read_bytes() for path in fixture.targets])

    def test_each_old_transaction_mismatch_blocks_first_write(self):
        for key in ('camera_rebind', 'summary_revision'):
            with self.subTest(key=key):
                fixture = self.fixture()
                path = Path(fixture.proposed[key]['stage']) / 'transaction.json'
                path.write_bytes(b'PUBLIC_FOREIGN_TRANSACTION')
                with self.assertRaises(ValueError):
                    fixture.invoke()
                self.assertEqual(fixture.old, [path.read_bytes() for path in fixture.targets])

    def test_foreign_intent_blocks_retry(self):
        fixture = self.fixture()
        fixture.fail_at = 'replace:source'
        with self.assertRaises(RuntimeError):
            fixture.invoke()
        state = fixture.journal()
        state['summary_followup']['stage'] = 'FOREIGN_STAGE'
        fixture.state_path.write_bytes(common.encoded(state))
        with self.assertRaises(ValueError):
            fixture.invoke()
        self.assertEqual(fixture.old[1:], [path.read_bytes() for path in fixture.targets[1:]])

    def test_changed_pause_or_owner_refuses(self):
        for key in ('pause', 'owner_valid'):
            with self.subTest(key=key):
                fixture = self.fixture()
                setattr(fixture, key, key == 'pause')
                with self.assertRaises(ValueError):
                    fixture.invoke()
                self.assertEqual(fixture.old, [path.read_bytes() for path in fixture.targets])


def public_receipts():
    spec = common.proposed()
    spec['summary_followup']['state'] = 'APPLIED'
    spec['source_manifest_sha256'] = 'b' * 64
    ready = json.loads(common.pinned(common.EVIDENCE / 'ready.json', common.BASE_READY_SHA))
    ready['main_pid'] += 10000
    ready['gtk_pid'] += 10000
    products = {relative: row['sha256'] for relative, row in spec['summary_followup']['payload']['sources'].items()}
    installed = dict(status='SUMMARY_FOLLOWUP_SOURCE_APPLIED_UI_STOPPED', spec=spec, source_files=products,
        component_pins=380, changed_component_count=1, unchanged_component_count=379,
        transaction_sha256='c' * 64, production_bootstrap_verified=True, profiles_migration_verified=True,
        gui_configuration_bytes_unchanged=True, face_readback_unchanged=True, private_data_replayed=False,
        ui_started=False, service_stop_or_kill=False, listening_preference_changed=False)
    mapping = json.loads(common.pinned(common.EVIDENCE / 'source_mapping.json', common.BASE_MAPPING_SHA))
    mapping.update(status='SUMMARY_FOLLOWUP_SOURCE_AND_SERVICE_VERIFIED', source_files=products,
        startup_sha256=spec['startup_sha256'], source_manifest_sha256=spec['source_manifest_sha256'],
        component_pins=spec['component_sha256'], transaction_sha256=installed['transaction_sha256'])
    mapping['supervisor']['pid'] = ready['main_pid']
    mapping['gtk']['pid'] = ready['gtk_pid']
    return spec, ready, installed, mapping


class SealTests(unittest.TestCase):
    def setup_paths(self):
        directory = tempfile.TemporaryDirectory(prefix='public-v24-seal-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        canonical, evidence = root / 'canonical', root / 'evidence'
        canonical.mkdir()
        for name, source, pin in (('spec.json', 'spec.json', common.BASE_SPEC_SHA),
                                  ('actual_ready.json', 'ready.json', common.BASE_READY_SHA)):
            (canonical / name).write_bytes(common.pinned(common.EVIDENCE / source, pin))
        return evidence, canonical

    def test_seal_full_source_receipts_and_same_retry(self):
        with public_selection():
            spec, ready, installed, mapping = public_receipts()
            evidence, canonical = self.setup_paths()
            raws = {name: common.encoded(value) for name, value in
                (('spec.json', spec), ('ready.json', ready), ('installed.json', installed))}
            for _ in range(2):
                result = seal_followup.commit_local(raws, mapping, evidence=evidence, canonical=canonical)
                self.assertEqual('SUMMARY_FOLLOWUP_SOURCE_EVIDENCE_SEALED_CANONICAL_COMMITTED', result['status'])
            self.assertEqual(raws['spec.json'], (canonical / 'spec.json').read_bytes())

    def test_both_canonical_pointer_interruptions_roll_forward(self):
        with public_selection():
            spec, ready, installed, mapping = public_receipts()
            raws = {name: common.encoded(value) for name, value in
                (('spec.json', spec), ('ready.json', ready), ('installed.json', installed))}
            for filename in ('actual_ready.json', 'spec.json'):
                with self.subTest(filename=filename):
                    evidence, canonical = self.setup_paths()
                    atomic = seal_followup.atomic_file
                    stopped = False

                    def interrupted(path, raw):
                        nonlocal stopped
                        atomic(path, raw)
                        if path == canonical / filename and not stopped:
                            stopped = True
                            raise RuntimeError('PUBLIC_SEAL_INTERRUPTION')

                    with patch.object(seal_followup, 'atomic_file', interrupted), self.assertRaises(RuntimeError):
                        seal_followup.commit_local(raws, mapping, evidence=evidence, canonical=canonical)
                    seal_followup.commit_local(raws, mapping, evidence=evidence, canonical=canonical)
                    self.assertEqual(raws['spec.json'], (canonical / 'spec.json').read_bytes())

    def test_wrong_camera_or_two_changed_sources_refuse(self):
        with public_selection():
            spec, ready, installed, mapping = public_receipts()
            changed = copy.deepcopy(mapping)
            changed['camera']['pid'] = 1335
            with self.assertRaises(ValueError):
                seal_followup.validate_mapping(changed, spec, ready, installed)
            installed['changed_component_count'] = 2
            with self.assertRaises(ValueError):
                seal_followup.validate_mapping(mapping, spec, ready, installed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
