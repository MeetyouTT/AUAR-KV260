"""Offline public publisher tests. No candidate product has been selected."""
import ast
import base64
import contextlib
import copy
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import apply_summary_closed
import seal_summary
import summary_common as common
from rollforward import roll_forward


@contextlib.contextmanager
def public_selection():
    """An isolated comment-only fixture, never an actual approved payload."""
    with tempfile.TemporaryDirectory(prefix='public-summary-v23-') as directory:
        root = Path(directory)
        decision = root / 'public-decision.json'
        decision.write_bytes(b'{"scope":"PUBLIC_TRANSPORT_FIXTURE_NOT_A_MODEL_SELECTION"}\n')
        sources = {}
        for index, relative in enumerate(sorted(common.ALLOWED_PATHS)):
            path = root / ('public-source-' + str(index) + '.py')
            raw = common.original_source(relative) + b'\n# PUBLIC TRANSPORT FIXTURE ONLY\n'
            path.write_bytes(raw)
            sources[relative] = dict(before_sha256=common.OLD_SOURCE_PINS[relative], sha256=common.sha(raw), local_source=str(path))
        value = dict(baseline_spec_sha256=common.BASE_SPEC_SHA, sources=sources,
                     decision={'path': str(decision), 'sha256': common.sha(decision.read_bytes())})
        raw = common.encoded(value)
        expected = common.sha(raw)
        old_pinned = common.pinned
        def pinned(path, sha):
            if Path(path) == common.HERE / 'APPROVED_PAYLOAD.json':
                common.need(sha == expected, 'public_approval_hash_mismatch')
                return raw
            return old_pinned(path, sha)
        with patch.object(common, 'APPROVED_PAYLOAD_SHA', expected), patch.object(common, 'pinned', pinned):
            yield value


class SourceClosureTests(unittest.TestCase):
    def test_unselected_package_refuses_proposal_and_execution(self):
        with patch.object(common, 'PAYLOAD_FINALIZED', False), patch.object(common, 'APPROVED_PAYLOAD_SHA', None):
            with self.assertRaisesRegex(ValueError, 'selection_pending'):
                common.proposed()
            with self.assertRaisesRegex(ValueError, 'final_root_selected'):
                common.execute_remote('', {})

    def test_actual_380_sameboot_baseline(self):
        base = common.baseline()
        self.assertEqual(380, len(base['component_sha256']))
        self.assertEqual(229296, base['camera_owner']['camera_pid'])
        self.assertEqual(22, base['camera_rebind']['binding']['written_proof']['candidate_pin_count'])
        self.assertEqual(common.v22.publisher_remote(base), common.publisher_remote(base))

    def test_exact_two_sources_only_config_and_camera_preserved(self):
        with public_selection():
            base = common.baseline()
            proposed = common.proposed()
            self.assertEqual(common.ALLOWED_PATHS, {name for name in base['component_sha256']
                                                   if base['component_sha256'][name] != proposed['component_sha256'][name]})
            self.assertEqual(380, len(proposed['component_sha256']))
            for key in ('configuration_sha256', 'minor_prepared_configuration_path', 'camera_owner', 'camera_rebind',
                        'face_readback', 'expected_final_listening_enabled'):
                self.assertEqual(base[key], proposed[key])
            self.assertEqual(common.startup_for(proposed)['component_sha256'], proposed['component_sha256'])

    def test_protected_code_rejects_store_or_context_changes(self):
        for relative in common.ALLOWED_PATHS:
            raw = common.original_source(relative)
            self.assertNotEqual(common.protected_source_ast(relative, raw),
                                common.protected_source_ast(relative, raw + b'\nPUBLIC_UNAUTHORIZED_CONSTANT=1\n'))
        relative = 'board/runtime/board_memory_policy.py'
        raw = common.original_source(relative)
        changed = raw.replace(b'context_limit=2048', b'context_limit=1024', 1)
        self.assertNotEqual(common.protected_source_ast(relative, raw), common.protected_source_ast(relative, changed))

    def test_new_publisher_preserves_every_lifecycle_function_ast(self):
        with public_selection():
            old = common.publisher_remote(common.baseline())
            new = common.publisher_remote(common.proposed())
            functions = lambda source: {node.name: ast.dump(node, include_attributes=False)
                                        for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
            self.assertEqual(functions(old), functions(new))
            self.assertIn("rebind_tx.get('applied_spec_sha256')==" + repr(common.BASE_SPEC_SHA), new)
            self.assertIn('completed_summary_spec_changed', new)

    def test_generated_apply_publish_seal_parse_for_python39(self):
        with public_selection():
            spec = common.proposed()
            for source in (common.publisher_remote(spec), apply_summary_closed.build_remote(spec), seal_summary.build_remote(spec)):
                ast.parse(source, feature_version=(3, 9))
                self.assertIn('exact_reviewed_complete_same_boot_owner_chain_required', source)

    def test_other_component_config_camera_or_pause_changes_rejected(self):
        with public_selection():
            for key in ('component', 'config', 'camera', 'pause'):
                spec = common.proposed()
                if key == 'component':
                    spec['component_sha256']['tools/board_recording.py'] = '0' * 64
                elif key == 'config':
                    spec['configuration_sha256'] = '0' * 64
                elif key == 'camera':
                    spec['camera_owner']['camera_pid'] = 1335
                else:
                    spec['expected_final_listening_enabled'] = True
                with self.subTest(key=key), self.assertRaises(ValueError):
                    common.validate_spec(spec, allow_proposed=True)


class R3AstBoundaryTests(unittest.TestCase):
    """Public AST templates only. These do not select a product candidate."""
    POLAR = "POLAR_QUESTION = re.compile(r'(?<![不没])(?:会不会|能不能)')"
    BLOCK = """has_nonassertive_marker = (re.search(r'询问|提问|想知道|是否|能否|[?？]|无论|不管|不论', text) is not None or POLAR_QUESTION.search(text) is not None)
source_negation_text = POLAR_QUESTION.sub(' ', source['text']) if has_nonassertive_marker else source['text']
summary_negation_text = POLAR_QUESTION.sub(' ', text)
if (POLAR_QUESTION.search(source['text']) and not has_nonassertive_marker) or ((meta.get('negated') is True or NEGATION.search(source_negation_text)) and not NEGATION.search(summary_negation_text)):
    reasons.add('negation_missing')
"""

    def candidate_tree(self):
        original = common.original_source('common/board_memory.py')
        tree = ast.parse(original)
        negation = next(node for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == 'NEGATION' for target in node.targets))
        declaration = ast.get_source_segment(original.decode(), negation)
        tree.body.insert(tree.body.index(negation) + 1, ast.parse(self.POLAR).body[0])
        body, index, _ = common.original_negation_rule(tree)
        body[index:index+1] = ast.parse(self.BLOCK).body
        return original, tree, declaration

    @contextlib.contextmanager
    def reviewed(self, declaration):
        with patch.object(common, 'R3_REVIEWED_POLAR_DECLARATION', self.POLAR), \
             patch.object(common, 'R3_REVIEWED_NEGATION_DECLARATION', declaration), \
             patch.object(common, 'R3_REVIEWED_NEGATION_BLOCK', self.BLOCK):
            yield

    def test_r3_new_shapes_refused_until_exact_reviewed_snippets_bound(self):
        _, tree, _ = self.candidate_tree()
        with patch.object(common, 'R3_REVIEWED_POLAR_DECLARATION', None), self.assertRaisesRegex(ValueError, 'review_pending'):
            common.protected_source_ast('common/board_memory.py', ast.unparse(tree))

    def test_only_exact_four_node_block_normalizes_to_original(self):
        original, tree, declaration = self.candidate_tree()
        with self.reviewed(declaration):
            self.assertEqual(common.protected_source_ast('common/board_memory.py', original),
                             common.protected_source_ast('common/board_memory.py', ast.unparse(tree)))

    def test_changed_fixed_regex_test_or_rejection_body_refused(self):
        for part in ('regex', 'test', 'body', 'locals'):
            _, tree, declaration = self.candidate_tree()
            body, index, rule = common.original_negation_rule(tree)
            if part == 'regex':
                polar = next(node for node in tree.body if isinstance(node, ast.Assign)
                             and any(isinstance(target, ast.Name) and target.id == 'POLAR_QUESTION' for target in node.targets))
                polar.value = ast.parse("re.compile('.*')", mode='eval').body
            elif part == 'test':
                rule.test = ast.Constant(value=False)
            elif part == 'body':
                rule.body.append(ast.parse('reasons.clear()').body[0])
            else:
                body[index-3].value = ast.Constant(value=True)
            with self.subTest(part=part), self.reviewed(declaration), self.assertRaises(ValueError):
                common.protected_source_ast('common/board_memory.py', ast.unparse(tree))

    def test_unrelated_name_number_status_visual_and_store_changes_still_differ(self):
        replacements = [('protected_name_missing', 'changed_name_rule'),
                        ('protected_number_missing_or_changed', 'changed_number_rule'),
                        ('planned_status_missing', 'changed_plan_rule'),
                        ('observation_evidence_missing', 'changed_visual_rule'),
                        ('PRAGMA foreign_keys=ON', 'PRAGMA foreign_keys=OFF')]
        original, tree, declaration = self.candidate_tree()
        for before, after in replacements:
            changed = ast.unparse(tree).replace(before, after)
            self.assertIn(after, changed)
            with self.subTest(rule=before), self.reviewed(declaration):
                self.assertNotEqual(common.protected_source_ast('common/board_memory.py', original),
                                    common.protected_source_ast('common/board_memory.py', changed))

    def test_polar_import_only_allows_single_unaliased_name(self):
        relative = 'board/runtime/board_memory_policy.py'
        raw = common.original_source(relative)
        tree = ast.parse(raw)
        memory_import = next(node for node in tree.body if isinstance(node, ast.ImportFrom)
                             and node.module == 'common.board_memory')
        memory_import.names.append(ast.alias(name='POLAR_QUESTION', asname=None))
        with patch.object(common, 'R3_REVIEWED_POLAR_DECLARATION', self.POLAR):
            self.assertEqual(common.protected_source_ast(relative, raw), common.protected_source_ast(relative, ast.unparse(tree)))
            memory_import.names[-1].asname = 'OTHER_PATTERN'
            with self.assertRaises(ValueError):
                common.protected_source_ast(relative, ast.unparse(tree))

    def test_rejected_r1_r2_policy_hashes_are_denied(self):
        with public_selection() as value:
            for rejected in common.REJECTED_POLICY_SHAS:
                changed = copy.deepcopy(value)
                changed['sources']['board/runtime/board_memory_policy.py']['sha256'] = rejected
                raw = common.encoded(changed)
                digest = common.sha(raw)
                original_pinned = common.pinned
                def rejected_payload(path, expected):
                    if Path(path) == common.HERE / 'APPROVED_PAYLOAD.json':
                        self.assertEqual(digest, expected)
                        return raw
                    return original_pinned(path, expected)
                with self.subTest(hash=rejected), patch.object(common, 'APPROVED_PAYLOAD_SHA', digest), \
                     patch.object(common, 'pinned', rejected_payload), \
                     self.assertRaisesRegex(ValueError, 'real_model_rejected_prompt_candidate'):
                    common.approved_payload()


class ActualR3SourceTests(unittest.TestCase):
    def actual_sources(self):
        candidate = common.REPAIR / 'memory_negation_v23_candidate_r3'
        manifest = json.loads(common.pinned(candidate / 'SOURCE_MANIFEST.json',
                                            '447390dc0eb627b30cf9e2b57c147c8a5764cbfe4b9310c238e6fa0872955084'))
        return {relative: common.pinned(row['local_source'], row['after_sha256'])
                for relative, row in manifest['sources'].items()}

    def test_frozen_actual_r3_restores_both_complete_baseline_asts(self):
        for relative, raw in self.actual_sources().items():
            self.assertEqual(common.protected_source_ast(relative, common.original_source(relative)),
                             common.protected_source_ast(relative, raw))

    def test_intrinsic_question_branch_cannot_be_removed(self):
        tree = ast.parse(self.actual_sources()['common/board_memory.py'])
        body, index, _ = common.original_negation_rule(tree)
        assignment = body[index-3]
        self.assertIsInstance(assignment.value, ast.BoolOp)
        assignment.value = assignment.value.values[0]
        with self.assertRaisesRegex(ValueError, 'text_handling_diff_changed'):
            common.protected_source_ast('common/board_memory.py', ast.unparse(tree))

    def test_space_separator_in_both_text_views_is_mandatory(self):
        for offset in (-2, -1):
            tree = ast.parse(self.actual_sources()['common/board_memory.py'])
            body, index, _ = common.original_negation_rule(tree)
            value = body[index+offset].value
            call = value.body if isinstance(value, ast.IfExp) else value
            self.assertEqual(' ', call.args[0].value)
            call.args[0] = ast.Constant(value='')
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'text_handling_diff_changed'):
                common.protected_source_ast('common/board_memory.py', ast.unparse(tree))


class RollForwardTests(unittest.TestCase):
    def test_all_sixteen_four_target_mixtures(self):
        paths = ['memory', 'policy', 'startup', 'manifest']
        before = {path: ('OLD_' + path).encode() for path in paths}
        after = {path: ('NEW_' + path).encode() for path in paths}
        for choice in itertools.product((False, True), repeat=4):
            current = {path: (after if flag else before)[path] for path, flag in zip(paths, choice)}
            roll_forward(paths, {path: common.sha(raw) for path, raw in before.items()}, after,
                         read=current.__getitem__, replace=current.__setitem__, guard=lambda: None)
            self.assertEqual(after, current)

    def test_foreign_bytes_refused_before_any_write(self):
        current = dict.fromkeys(('memory', 'policy', 'startup', 'manifest'), b'old')
        current['policy'] = b'foreign'
        writes = []
        with self.assertRaises(ValueError):
            roll_forward(list(current), dict.fromkeys(current, common.sha(b'old')), dict.fromkeys(current, b'new'),
                         read=current.__getitem__, replace=lambda *args: writes.append(args), guard=lambda: None)
        self.assertEqual([], writes)


def prior_public_fixture_class():
    path = common.PREVIOUS / 'test_rebind.py'
    common.pinned(path, 'eeb48cad14432b5b4a2411f93888fe901011312de5027d00d4d34b9e36015218')
    sys.path.insert(0, str(common.PREVIOUS))
    spec = importlib.util.spec_from_file_location('_v22_public_fixture_for_summary', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PublicApplyFixture


class PublicMemoryFixture(prior_public_fixture_class()):
    def __init__(self, directory):
        super().__init__(directory)
        self.source_paths = ['common/board_memory.py', 'board/runtime/board_memory_policy.py']
        self.gui_raw = common.encoded(self.base_gui)
        self.new_gui = copy.deepcopy(self.base_gui)
        self.stage = self.control / 'memory-summary-v23-public'
        self.new_raws = {relative: b'PUBLIC_VALUE=2\n' for relative in self.source_paths}
        for index, relative in enumerate(self.source_paths):
            self.base_pins.pop('public/component_' + str(index) + '.py')
            self.base_pins[relative] = common.sha(b'PUBLIC_VALUE=1\n')
        self.base_startup = {'runtime': str(self.root / 'runtime'), 'component_sha256': self.base_pins}
        self.old_manifest.update(component_pins=self.base_pins)
        self.targets = [self.root / 'runtime/aura' / relative for relative in self.source_paths]
        self.targets += [self.root / 'startup/config.json', self.root / 'production_source_manifest.json']
        for path, raw in zip(self.targets, [b'PUBLIC_VALUE=1\n'] * 2 + [common.encoded(self.base_startup), common.encoded(self.old_manifest)]):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.old = [path.read_bytes() for path in self.targets]
        self.new_pins = dict(self.base_pins)
        self.sources = {}
        for relative in self.source_paths:
            self.new_pins[relative] = common.sha(self.new_raws[relative])
            self.sources[relative] = dict(before_sha256=self.base_pins[relative], sha256=self.new_pins[relative], local_source='PUBLIC_LOCAL_ONLY')
        self.new_startup = dict(self.base_startup, component_sha256=self.new_pins)
        camera_stage = self.control / 'prior-camera-rebind'
        camera_stage.mkdir()
        camera_tx = common.encoded({'applied_spec_sha256': common.BASE_SPEC_SHA})
        (camera_stage / 'transaction.json').write_bytes(camera_tx)
        self.proposed = dict(target=str(self.root), boot_id='PUBLIC_BOOT', component_sha256=self.new_pins,
                             configuration_sha256=common.sha(self.gui_raw), startup_sha256=common.sha(common.encoded(self.new_startup)),
                             source_manifest_sha256='0' * 64, minor_prepared_configuration_path=str(self.external),
                             camera_owner={'camera_pid': 229296}, camera_rebind={'stage': str(camera_stage)},
                             summary_revision={'stage': str(self.stage), 'state': 'PROPOSED', 'payload': {'sources': self.sources}})
        self.initial_journal['camera_rebind'] = dict(state='APPLIED', stage=str(camera_stage), transaction_sha256=common.sha(camera_tx))
        self.state_path.write_bytes(common.encoded(self.initial_journal))

    def atomic(self, path, raw):
        Path(path).write_bytes(raw)
        if Path(path) in self.targets:
            self.checkpoint('replace:' + ('memory', 'policy', 'startup', 'manifest')[self.targets.index(Path(path))])

    def invoke(self):
        self.lease_count = 0
        fake_os = types.SimpleNamespace(**{key: getattr(os, key) for key in ('open', 'fdopen', 'fsync', 'close', 'O_RDWR', 'O_RDONLY')})
        fake_os.O_NOFOLLOW = getattr(os, 'O_NOFOLLOW', 0)
        fake_os.O_DIRECTORY = getattr(os, 'O_DIRECTORY', 0)
        fake_os.geteuid = getattr(os, 'geteuid', lambda: self.control.stat().st_uid)
        def flock(*unused):
            self.lease_count += 1
        c = types.SimpleNamespace(read=self.read, parse=json.loads, encoded=common.encoded, sha=common.sha,
                                  create=self.create, relative=lambda value: value, show=lambda: {'ActiveState': 'inactive'})
        namespace = dict(Path=self.path, os=fake_os, c=c, sys=sys,
                         fcntl=types.SimpleNamespace(flock=flock, LOCK_EX=1, LOCK_NB=2),
                         boot=self.guard, journal=self.journal, inactive=self.guard, ownerless=self.guard,
                         guarded=self.guard, reviewed_face=self.guard, source=self.guard, need=common.need,
                         save=self.save, atomic=self.atomic, SPEC=copy.deepcopy(self.proposed),
                         CONTROL=self.control, STATE=self.state_path, EXACT_TARGET=str(self.root), REVISION=common.REVISION,
                         BASE_PINS=self.base_pins, BASE_STARTUP=self.base_startup,
                         BASE_CONFIG_SHA=common.sha(self.gui_raw), BASE_STARTUP_SHA=common.sha(self.old[2]),
                         BASE_MANIFEST_SHA=common.sha(self.old[3]), BASE_SPEC_SHA=common.BASE_SPEC_SHA,
                         BASE_SOURCE_PINS={relative: self.base_pins[relative] for relative in self.source_paths},
                         SOURCE_PATHS=self.source_paths, CONFIGURATION_PATH=str(self.external),
                         LAUNCHER_SHA=common.sha(b'PUBLIC_LAUNCHER'), EXPECTED_GUI=self.base_gui, EXPECTED_STARTUP=self.new_startup,
                         PAYLOAD={relative: dict(row, base64=base64.b64encode(self.new_raws[relative]).decode())
                                  for relative, row in self.sources.items()})
        exec(compile(apply_summary_closed.original_transaction_helpers(), '<pinned-original-helper-public-test>', 'exec'), namespace)
        tree = ast.parse((common.HERE / 'apply_runtime.py').read_bytes())
        definitions = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<exact-public-memory-apply>', 'exec'), namespace)
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
            return namespace['apply_summary']()


class ActualApplyFunctionTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix='public-memory-apply-v23-')
        self.addCleanup(directory.cleanup)
        return PublicMemoryFixture(directory.name)

    def test_complete_then_result_lost_retry(self):
        fixture = self.fixture()
        result = fixture.invoke()
        self.assertEqual('SUMMARY_MEMORY_SOURCES_APPLIED_UI_STOPPED', result['status'])
        self.assertEqual(result, fixture.invoke())
        self.assertEqual(fixture.gui_raw, fixture.external.read_bytes())
        self.assertEqual(380, len(fixture.base_pins))

    def test_twelve_interruptions_recover_only_forward(self):
        points = ['create:memory-core.py', 'create:production-source-manifest.json', 'create:prepared-memory.py',
                  'create:prepared-policy.py', 'create:transaction.json', 'fsync:before', 'journal:SUMMARY_SOURCE_INTENT',
                  'replace:memory', 'replace:policy', 'replace:startup', 'replace:manifest', 'journal:NORMAL_CLOSED']
        for point in points:
            with self.subTest(point=point):
                fixture = self.fixture()
                fixture.fail_at = point
                with self.assertRaisesRegex(RuntimeError, 'PUBLIC_INJECTED_INTERRUPTION'):
                    fixture.invoke()
                self.assertEqual('SUMMARY_MEMORY_SOURCES_APPLIED_UI_STOPPED', fixture.invoke()['status'])
                self.assertEqual(fixture.gui_raw, fixture.external.read_bytes())

    def test_all_intent_mixtures_preserve_camera_and_gui(self):
        for choice in itertools.product((False, True), repeat=4):
            with self.subTest(choice=choice):
                fixture = self.fixture()
                fixture.fail_at = 'replace:manifest'
                with self.assertRaises(RuntimeError):
                    fixture.invoke()
                expected = [path.read_bytes() for path in fixture.targets]
                for path, flag, before, after in zip(fixture.targets, choice, fixture.old, expected):
                    path.write_bytes(after if flag else before)
                fixture.invoke()
                self.assertEqual(expected, [path.read_bytes() for path in fixture.targets])
                self.assertEqual(fixture.initial_journal['camera_rebind'], fixture.journal()['camera_rebind'])

    def test_unrelated_source_change_blocks_remaining_writes(self):
        fixture = self.fixture()
        fixture.fail_at = 'replace:memory'
        with self.assertRaises(RuntimeError):
            fixture.invoke()
        key = str(fixture.root / 'runtime/aura/public/component_2.py')
        fixture.readonly[key] = b'FOREIGN_PUBLIC_BYTES'
        with self.assertRaises(ValueError):
            fixture.invoke()
        self.assertEqual(fixture.old[1:], [path.read_bytes() for path in fixture.targets[1:]])
        self.assertEqual('SUMMARY_SOURCE_INTENT', fixture.journal()['phase'])

    def test_camera_transaction_mismatch_refused(self):
        fixture = self.fixture()
        camera_tx = Path(fixture.proposed['camera_rebind']['stage']) / 'transaction.json'
        camera_tx.write_bytes(b'PUBLIC_FOREIGN_TRANSACTION')
        with self.assertRaises(ValueError):
            fixture.invoke()
        self.assertEqual(fixture.old, [path.read_bytes() for path in fixture.targets])


def public_receipts():
    spec = common.proposed()
    spec['summary_revision']['state'] = 'APPLIED'
    spec['source_manifest_sha256'] = 'a' * 64
    ready = dict(status='PRODUCTION_BOARD_BUSINESS_READY', root=spec['target'], guard_removed=True,
                 data_origin='board', listening_enabled=False, listening_state='PAUSED',
                 physical_microphone_opened=False, retention_enabled=True, main_pid=400001, gtk_pid=400002)
    products = {relative: row['sha256'] for relative, row in spec['summary_revision']['payload']['sources'].items()}
    installed = dict(status='SUMMARY_MEMORY_SOURCES_APPLIED_UI_STOPPED', spec=spec, source_files=products,
                     component_pins=380, changed_component_count=2, unchanged_component_count=378,
                     production_bootstrap_verified=True, profiles_migration_verified=True,
                     gui_configuration_bytes_unchanged=True, face_readback_unchanged=True,
                     private_data_replayed=False, ui_started=False, service_stop_or_kill=False,
                     listening_preference_changed=False, transaction_sha256='b' * 64)
    mapping = json.loads(common.pinned(common.EVIDENCE / 'source_mapping.json', common.BASE_MAPPING_SHA))
    mapping.update(status='SUMMARY_SOURCE_AND_SERVICE_VERIFIED', startup_sha256=spec['startup_sha256'],
                   source_manifest_sha256=spec['source_manifest_sha256'], component_pins=spec['component_sha256'],
                   source_files=products, transaction_sha256=installed['transaction_sha256'])
    mapping['supervisor']['pid'] = ready['main_pid']
    mapping['gtk']['pid'] = ready['gtk_pid']
    raws = {name + '.json': common.encoded(value) for name, value in
            (('spec', spec), ('ready', ready), ('installed', installed))}
    return spec, ready, installed, mapping, raws


class SealTests(unittest.TestCase):
    def paths(self):
        directory = tempfile.TemporaryDirectory(prefix='public-memory-seal-v23-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        canonical = root / 'canonical'
        canonical.mkdir()
        (canonical / 'spec.json').write_bytes(common.pinned(common.EVIDENCE / 'spec.json', common.BASE_SPEC_SHA))
        (canonical / 'actual_ready.json').write_bytes(common.pinned(common.EVIDENCE / 'ready.json', common.BASE_READY_SHA))
        return canonical, root / 'evidence'

    def test_seal_preserves_baseline_and_retries_same_receipt(self):
        with public_selection():
            _, _, _, mapping, raws = public_receipts()
            canonical, evidence = self.paths()
            result = seal_summary.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
            self.assertEqual('SUMMARY_SOURCE_EVIDENCE_SEALED_CANONICAL_COMMITTED', result['status'])
            self.assertEqual(result, seal_summary.commit_local(raws, mapping, canonical=canonical, evidence=evidence))
            self.assertEqual(raws['spec.json'], (canonical / 'spec.json').read_bytes())
            self.assertEqual(common.BASE_SPEC_SHA, common.sha((evidence / 'previous_canonical_spec.json').read_bytes()))

    def test_two_canonical_pointer_interruptions_resume(self):
        with public_selection():
            for target in ('actual_ready.json', 'spec.json'):
                _, _, _, mapping, raws = public_receipts()
                canonical, evidence = self.paths()
                original = seal_summary.atomic_file
                def interrupt(path, raw):
                    original(path, raw)
                    if path.parent == canonical and path.name == target:
                        raise RuntimeError('PUBLIC_SEAL_INTERRUPTION')
                with patch.object(seal_summary, 'atomic_file', interrupt), self.assertRaises(RuntimeError):
                    seal_summary.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
                self.assertTrue((evidence / 'source_mapping.json').exists())
                seal_summary.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
                self.assertEqual(raws['spec.json'], (canonical / 'spec.json').read_bytes())

    def test_false_bool_aliases_and_changed_camera_or_source_rejected(self):
        with public_selection():
            for key in ('version_alias', 'enabled_alias', 'microphone_alias', 'camera', 'config', 'source', 'commit'):
                spec, ready, installed, mapping, _ = public_receipts()
                mapping = copy.deepcopy(mapping)
                if key == 'version_alias':
                    mapping['saved_listening_preference']['version'] = True
                elif key == 'enabled_alias':
                    mapping['listening']['enabled'] = 0
                elif key == 'microphone_alias':
                    mapping['listening']['microphone_open'] = 0
                elif key == 'camera':
                    mapping['camera']['pid'] = 1335
                elif key == 'config':
                    mapping['configuration_sha256'] = 'c' * 64
                elif key == 'source':
                    mapping['component_pins']['common/board_memory.py'] = 'c' * 64
                else:
                    mapping['current_publication_committed'] = False
                with self.subTest(key=key), self.assertRaises(ValueError):
                    seal_summary.validate_mapping(mapping, spec, ready, installed)

    def test_other_canonical_blocks_writes(self):
        with public_selection():
            _, _, _, mapping, raws = public_receipts()
            canonical, evidence = self.paths()
            (canonical / 'spec.json').write_bytes(b'PUBLIC_OTHER_RELEASE')
            with self.assertRaises(ValueError):
                seal_summary.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
            self.assertFalse(evidence.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
