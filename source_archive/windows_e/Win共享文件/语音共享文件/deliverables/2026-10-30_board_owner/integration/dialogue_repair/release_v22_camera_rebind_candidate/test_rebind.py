"""Public fixtures only. No SSH, service, camera, model or private DB access."""
import ast
import copy
import contextlib
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import apply_rebind_closed
import rebind_common as common
from rollforward import roll_forward
import seal_rebind


def public_binding():
    _, restored = common.load_camera_modules()
    authority = dict(restored.FIXED, candidate_pid=200002, restored_pid=200003,
                     checkpoint_sha256='a' * 64, journal_sha256='b' * 64)
    owner = dict(board_boot_id=authority['boot'], camera_pid=authority['restored_pid'],
                 camera_start_ticks='123456', camera_cmdline_sha256='c' * 64)
    proof = dict(ready=True, status='SAME_BOOT_READBACK_CANDIDATE_WRITTEN_NOT_INSTALLED', owner=owner,
                 original_pin_count=21, candidate_pin_count=22, candidate_sha256='d' * 64,
                 observation_sha256='e' * 64, journal_sha256=authority['journal_sha256'],
                 executor_sha256=authority['executor_sha256'], latest_consumed_checkpoint_sha256=authority['checkpoint_sha256'],
                 new_runtime_sha256='f' * 64, private_original_config_changed=False, database_opened=False,
                 native_runner_loaded=False, service_action_sent=False, checkpoint_or_marker_modified=False,
                 new_boot_admission_used=False, written=True)
    return dict(authority=authority, authority_sha256=common.sha(common.encoded(authority)), written_proof=proof,
                written_proof_sha256=common.sha(common.encoded(proof)),
                face_path='/home/root/aura-board-owner-candidate-20261030/PUBLIC_FIXTURE_ONLY/readback.json')


def public_applied():
    spec = common.proposed(public_binding())
    spec['camera_rebind']['state'] = 'APPLIED'
    spec['source_manifest_sha256'] = '1' * 64
    return spec


class BindingTests(unittest.TestCase):
    def test_actual_v21_baseline_pins(self):
        value = common.baseline()
        self.assertEqual(380, len(value['component_sha256']))
        self.assertEqual(common.REMOTE_SHA, common.sha(common.publisher_remote(value).encode()))

    def test_only_face_config_and_one_component_changes(self):
        binding = public_binding()
        config = common.configuration_for(binding)
        config['board_business']['face_readback'] = common.literal('EXPECTED_GUI')['board_business']['face_readback']
        self.assertEqual(common.literal('EXPECTED_GUI'), config)
        base = common.baseline()
        proposed = common.proposed(binding)
        changed = {name for name in base['component_sha256'] if base['component_sha256'][name] != proposed['component_sha256'][name]}
        self.assertEqual({common.CONFIG_RELATIVE}, changed)
        self.assertEqual(380, len(proposed['component_sha256']))
        startup = common.startup_for(proposed)
        startup['component_sha256'][common.CONFIG_RELATIVE] = common.BASE_CONFIG_SHA
        self.assertEqual(common.literal('EXPECTED_STARTUP'), startup)
        self.assertNotIn('camera_owner', startup)

    def test_lifecycle_ast_unchanged(self):
        old = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(common.frozen_remote()).body
               if isinstance(node, ast.FunctionDef)}
        new = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(common.publisher_remote(public_applied())).body
               if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(old), set(new))
        self.assertEqual({'reviewed_face'}, {name for name in old if old[name] != new[name]})

    def test_reject_cross_boot_old_owner_or_bad_proof(self):
        edits = [('authority', 'boot', 'wrong-boot'), ('authority', 'restored_pid', 1335),
                 ('written_proof', 'candidate_pin_count', 21), ('written_proof', 'written', False),
                 ('written_proof', 'journal_sha256', '7' * 64), ('written_proof', 'new_boot_admission_used', True)]
        for section, key, value in edits:
            with self.subTest(key=key):
                binding = public_binding()
                binding[section][key] = value
                with self.assertRaises(ValueError):
                    common.proposed(binding)

    def test_spec_rejects_other_config_source_or_pause_change(self):
        for key in ('source', 'pause', 'camera', 'stage'):
            spec = public_applied()
            if key == 'source':
                spec['component_sha256']['tools/board_avatar_gtk.py'] = '8' * 64
            elif key == 'pause':
                spec['expected_final_listening_enabled'] = True
            elif key == 'camera':
                spec['camera_owner']['camera_pid'] += 1
            else:
                spec['minor_prepared_configuration_path'] += '.other'
            with self.subTest(key=key), self.assertRaises(ValueError):
                common.validate_spec(spec)

    def test_old_spec_cannot_start_and_proposed_cannot_publish(self):
        with self.assertRaises(ValueError):
            common.validate_spec(common.baseline())
        with self.assertRaises(ValueError):
            common.validate_spec(common.proposed(public_binding()))
        common.validate_spec(public_applied())

    def test_remote_bodies_parse_for_supported_python(self):
        spec = common.proposed(public_binding())
        for source in (apply_rebind_closed.build_remote(spec), common.publisher_remote(public_applied()),
                       seal_rebind.build_remote(public_applied())):
            ast.parse(source, feature_version=(3, 9))
            self.assertIn('exact_reviewed_complete_same_boot_owner_chain_required', source)
            self.assertNotIn("subprocess.run(['kill'", source)


class RollForwardTests(unittest.TestCase):
    def test_all_eight_old_new_combinations(self):
        paths = ['gui', 'startup', 'manifest']
        old = {p: ('old ' + p).encode() for p in paths}
        new = {p: ('new ' + p).encode() for p in paths}
        for combination in itertools.product((False, True), repeat=3):
            contents = {p: (new if after else old)[p] for p, after in zip(paths, combination)}
            roll_forward(paths, {p: common.sha(raw) for p, raw in old.items()}, new,
                         read=contents.__getitem__, replace=contents.__setitem__, guard=lambda: None)
            self.assertEqual(new, contents)

    def test_foreign_target_blocks_every_write(self):
        current = {'gui': b'old', 'startup': b'foreign', 'manifest': b'old'}
        writes = []
        with self.assertRaises(ValueError):
            roll_forward(list(current), {p: common.sha(b'old') for p in current}, {p: b'new' for p in current},
                         read=current.__getitem__, replace=lambda *args: writes.append(args), guard=lambda: None)
        self.assertEqual([], writes)

    def test_guard_failure_stops_following_targets(self):
        current = dict.fromkeys(('gui', 'startup', 'manifest'), b'old')
        writes = []
        def guard():
            if writes:
                raise ValueError('owner_changed')
        def replace(name, raw):
            writes.append(name)
            current[name] = raw
        with self.assertRaisesRegex(ValueError, 'owner_changed'):
            roll_forward(list(current), {p: common.sha(b'old') for p in current}, {p: b'new' for p in current},
                         read=current.__getitem__, replace=replace, guard=guard)
        self.assertEqual(['gui'], writes)


class PublicApplyFixture:
    """Executes the actual apply_rebind function with bounded public IO adapters."""
    def __init__(self, directory):
        self.home = Path(directory)
        self.root = self.home / 'runtime-root'
        self.control = self.home / 'control'
        self.private = self.home / 'private'
        self.stage = self.control / 'camera-owner-rebind-v22-public'
        for directory in (self.root, self.control, self.private, self.private / 'speaker'):
            directory.mkdir(mode=0o700)
        self.ui_lock = self.home / 'ui.lock'
        for path in (self.ui_lock, self.private / 'writer.lock', self.private / 'speaker/speaker-writer.lock'):
            path.write_bytes(b'')
        self.fail_at = None
        self.failure_consumed = False
        self.events = []
        self.lease_count = 0
        self.bootstrap_count = 0
        self.owner_valid = True
        self.pause = False
        self.readonly = {}
        rel = common.CONFIG_RELATIVE
        self.base_gui = {'board_business': {'face_readback': {'path': 'public-old.json', 'sha256': '0' * 64},
                                            'bootstrap_receipt': 'public-receipt', 'bootstrap_receipt_sha256': '1' * 64}}
        self.new_gui = copy.deepcopy(self.base_gui)
        self.new_gui['board_business']['face_readback'] = {'path': 'public-new.json', 'sha256': '2' * 64}
        self.base_pins = {f'public/component_{index}.py': common.sha(b'PUBLIC_COMPONENT') for index in range(379)}
        self.base_pins[rel] = common.sha(common.encoded(self.base_gui))
        for relative in self.base_pins:
            if relative != rel:
                self.readonly[str(self.root / 'runtime/aura' / relative)] = b'PUBLIC_COMPONENT'
        self.base_startup = {'runtime': str(self.root / 'runtime'), 'component_sha256': self.base_pins}
        self.external = self.home / 'old-external.json'
        self.external.write_bytes(common.encoded(self.base_gui))
        self.old_manifest = {'component_pins': self.base_pins, 'configuration_sha256': self.base_pins[rel],
                             'configuration_path': str(self.external), 'files': {}}
        self.targets = [self.root / 'runtime/aura' / rel, self.root / 'startup/config.json',
                        self.root / 'production_source_manifest.json']
        for path, value in zip(self.targets, (self.base_gui, self.base_startup, self.old_manifest)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(common.encoded(value))
        self.old = [path.read_bytes() for path in self.targets]
        self.readonly[str(self.root / 'startup/launcher.py')] = b'PUBLIC_LAUNCHER'
        self.new_pins = dict(self.base_pins, **{rel: common.sha(common.encoded(self.new_gui))})
        self.new_startup = dict(self.base_startup, component_sha256=self.new_pins)
        self.proposed = dict(target=str(self.root), boot_id='PUBLIC_BOOT', component_sha256=self.new_pins,
                             configuration_sha256=self.new_pins[rel], startup_sha256=common.sha(common.encoded(self.new_startup)),
                             source_manifest_sha256='0' * 64, minor_prepared_configuration_path=str(self.stage / 'prepared-gui.json'),
                             camera_owner={'camera_pid': 200003}, face_readback=self.new_gui['board_business']['face_readback'],
                             camera_rebind={'stage': str(self.stage), 'state': 'PROPOSED',
                                            'binding': {'written_proof': {'observation_sha256': 'e' * 64}}})
        self.state_path = self.control / 'state.json'
        self.initial_journal = dict(phase='NORMAL_CLOSED', boot_id='PUBLIC_BOOT', guard_removed=False, active_root=str(self.root))
        self.state_path.write_bytes(common.encoded(self.initial_journal))

    def checkpoint(self, name):
        self.events.append(name)
        if self.fail_at == name and not self.failure_consumed:
            self.failure_consumed = True
            raise RuntimeError('PUBLIC_INJECTED_INTERRUPTION')

    def path(self, value):
        value = str(value)
        mapping = {'/home/root/.local/share/aura-board-business': self.private, '/run/aura-avatar-ui.lock': self.ui_lock}
        return Path(mapping.get(value, value))

    def read(self, path, pin=None):
        path = str(path)
        if path == '/home/root/.local/share/aura-board-business/listening_preference.json':
            raw = common.encoded({'version': 1, 'enabled': self.pause})
        elif path in self.readonly:
            raw = self.readonly[path]
        else:
            raw = Path(path).read_bytes()
        if pin is not None:
            common.need(common.sha(raw) == pin, 'public_pin_mismatch')
        return raw

    def create(self, path, raw):
        with Path(path).open('xb') as stream:
            stream.write(raw)
        self.checkpoint('create:' + Path(path).name)

    def atomic(self, path, raw):
        Path(path).write_bytes(raw)
        if Path(path) in self.targets:
            self.checkpoint('replace:' + ('gui', 'startup', 'manifest')[self.targets.index(Path(path))])

    def journal(self):
        return json.loads(self.state_path.read_bytes())

    def save(self, value):
        self.state_path.write_bytes(common.encoded(value))
        self.checkpoint('journal:' + value['phase'])

    def guard(self, *unused):
        common.need(self.owner_valid, 'public_owner_changed')

    def bootstrap(self, *unused):
        self.bootstrap_count += 1
        common.need(self.lease_count == 3, 'three_original_leases_required_before_bootstrap')
        return {'profiles_migration_verified': True}

    def invoke(self):
        self.lease_count = 0
        spec = copy.deepcopy(self.proposed)
        fake_os = types.SimpleNamespace(**{key: getattr(os, key) for key in ('open', 'fdopen', 'fsync', 'close', 'O_RDWR', 'O_RDONLY')})
        fake_os.O_NOFOLLOW = getattr(os, 'O_NOFOLLOW', 0)
        fake_os.O_DIRECTORY = getattr(os, 'O_DIRECTORY', 0)
        fake_os.geteuid = getattr(os, 'geteuid', lambda: self.stage.parent.stat().st_uid)
        def flock(*unused):
            self.lease_count += 1
        c = types.SimpleNamespace(read=self.read, parse=json.loads, encoded=common.encoded, sha=common.sha,
                                  create=self.create, relative=lambda value: value,
                                  show=lambda: {'ActiveState': 'inactive'})
        namespace = dict(Path=self.path, os=fake_os, c=c, sys=sys,
                         fcntl=types.SimpleNamespace(flock=flock, LOCK_EX=1, LOCK_NB=2),
                         boot=self.guard, journal=self.journal, inactive=self.guard, ownerless=self.guard,
                         guarded=self.guard, reviewed_face=self.guard, source=self.guard, need=common.need,
                         save=self.save, atomic=self.atomic, roll_forward=roll_forward, SPEC=spec,
                         CONTROL=self.control, STATE=self.state_path, EXACT_TARGET=str(self.root), REVISION=common.REVISION,
                         BASE_PINS=self.base_pins, BASE_STARTUP=self.base_startup, BASE_GUI=self.base_gui,
                         BASE_CONFIG_SHA=common.sha(self.old[0]), BASE_STARTUP_SHA=common.sha(self.old[1]),
                         BASE_MANIFEST_SHA=common.sha(self.old[2]), CONFIG_RELATIVE=common.CONFIG_RELATIVE,
                         LAUNCHER_SHA=common.sha(b'PUBLIC_LAUNCHER'), OLD_EXTERNAL_PATH=str(self.external),
                         EXPECTED_GUI=self.new_gui, EXPECTED_STARTUP=self.new_startup)
        tree = ast.parse((common.HERE / 'apply_runtime.py').read_bytes())
        definitions = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<exact-public-apply-runtime>', 'exec'), namespace)
        # Windows cannot open directories for fsync. This adapter changes only
        # that OS primitive, retaining the actual transaction function bytecode.
        namespace['fsync_directory'] = lambda path: self.checkpoint('fsync:' + Path(path).name)
        if os.name == 'nt':
            def windows_private_directory(path):
                path = Path(path)
                path.mkdir(exist_ok=True)
                common.need(path.resolve() == path and not path.is_symlink() and path.is_dir(),
                            'public_transaction_directory_redirected')
            # Windows lacks POSIX ownership/mode bits. Linux uses the original
            # function. The transaction itself is executed unchanged on both.
            namespace['private_directory'] = windows_private_directory
        module = types.ModuleType('common.board_production_bootstrap')
        module.verify_production_bootstrap = self.bootstrap
        package = types.ModuleType('common')
        package.__path__ = []
        with patch.dict(sys.modules, {'common': package, 'common.board_production_bootstrap': module}):
            return namespace['apply_rebind']()


class ApplyRuntimeTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory(prefix='public-rebind-v22-')
        self.addCleanup(directory.cleanup)
        return PublicApplyFixture(directory.name)

    def test_complete_normal_transaction_and_idempotent_receipt_retry(self):
        fixture = self.fixture()
        result = fixture.invoke()
        self.assertEqual('CAMERA_OWNER_REBOUND_UI_STOPPED', result['status'])
        before = [path.read_bytes() for path in fixture.targets]
        again = fixture.invoke()
        self.assertEqual(result, again)
        self.assertEqual(before, [path.read_bytes() for path in fixture.targets])
        self.assertEqual(fixture.old[0], fixture.external.read_bytes())

    def test_interruptions_before_intent_after_every_target_and_after_done(self):
        points = ['create:gui-config.json', 'create:production-source-manifest.json', 'create:prepared-gui.json',
                  'create:applied-spec.json', 'create:transaction.json', 'fsync:before',
                  'journal:CAMERA_REBIND_INTENT', 'replace:gui', 'replace:startup', 'replace:manifest',
                  'journal:NORMAL_CLOSED']
        for point in points:
            with self.subTest(point=point):
                fixture = self.fixture()
                fixture.fail_at = point
                with self.assertRaisesRegex(RuntimeError, 'PUBLIC_INJECTED_INTERRUPTION'):
                    fixture.invoke()
                if fixture.journal()['phase'] == 'NORMAL_CLOSED' and 'camera_rebind' not in fixture.journal():
                    self.assertEqual(fixture.old, [path.read_bytes() for path in fixture.targets])
                result = fixture.invoke()
                self.assertEqual('CAMERA_OWNER_REBOUND_UI_STOPPED', result['status'])
                self.assertEqual('APPLIED', fixture.journal()['camera_rebind']['state'])
                self.assertEqual(fixture.old[0], fixture.external.read_bytes())

    def test_resumed_intent_all_old_new_mixed_states(self):
        for combination in itertools.product((False, True), repeat=3):
            with self.subTest(combination=combination):
                fixture = self.fixture()
                fixture.fail_at = 'replace:manifest'
                with self.assertRaises(RuntimeError):
                    fixture.invoke()
                new = [path.read_bytes() for path in fixture.targets]
                for path, use_new, old, raw in zip(fixture.targets, combination, fixture.old, new):
                    path.write_bytes(raw if use_new else old)
                fixture.invoke()
                self.assertEqual(new, [path.read_bytes() for path in fixture.targets])

    def test_unowned_mixed_target_rejected_without_intent(self):
        fixture = self.fixture()
        fixture.targets[0].write_bytes(common.encoded(fixture.new_gui))
        with self.assertRaises(ValueError):
            fixture.invoke()
        self.assertNotIn('camera_rebind', fixture.journal())

    def test_foreign_target_in_intent_retains_guard_without_more_writes(self):
        fixture = self.fixture()
        fixture.fail_at = 'replace:gui'
        with self.assertRaises(RuntimeError):
            fixture.invoke()
        fixture.targets[1].write_bytes(b'FOREIGN_PUBLIC_BYTES')
        count = len([x for x in fixture.events if x.startswith('replace:')])
        with self.assertRaisesRegex(ValueError, 'outside_reviewed_old_new'):
            fixture.invoke()
        self.assertEqual(count, len([x for x in fixture.events if x.startswith('replace:')]))
        self.assertEqual('CAMERA_REBIND_INTENT', fixture.journal()['phase'])

    def test_changed_saved_pause_or_owner_refused(self):
        for field in ('pause', 'owner'):
            fixture = self.fixture()
            if field == 'pause':
                fixture.pause = True
            else:
                fixture.owner_valid = False
            with self.subTest(field=field), self.assertRaises(ValueError):
                fixture.invoke()
            self.assertEqual(fixture.old, [path.read_bytes() for path in fixture.targets])


def public_seal_inputs():
    spec = public_applied()
    ready = dict(status='PRODUCTION_BOARD_BUSINESS_READY', root=spec['target'], guard_removed=True,
                 data_origin='board', listening_enabled=False, listening_state='PAUSED',
                 physical_microphone_opened=False, retention_enabled=True, main_pid=300001, gtk_pid=300002)
    installed = dict(status='CAMERA_OWNER_REBOUND_UI_STOPPED', spec=spec,
                     source_files={common.CONFIG_RELATIVE: spec['configuration_sha256']}, component_pins=380,
                     changed_component_count=1, unchanged_component_count=379,
                     production_bootstrap_verified=True, profiles_migration_verified=True,
                     previous_configuration_preserved=True,
                     previous_configuration_path=common.baseline()['minor_prepared_configuration_path'],
                     configuration_sha256=spec['configuration_sha256'], configuration_path=spec['minor_prepared_configuration_path'],
                     private_data_replayed=False, ui_started=False, service_stop_or_kill=False,
                     listening_preference_changed=False, transaction_sha256='2' * 64)
    mapping = dict(status='CAMERA_REBIND_SOURCE_AND_SERVICE_VERIFIED', observed_mono=12345.5,
                   boot_id=spec['boot_id'], root=spec['target'], startup_sha256=spec['startup_sha256'],
                   source_manifest_sha256=spec['source_manifest_sha256'], configuration_sha256=spec['configuration_sha256'],
                   configuration_path=spec['minor_prepared_configuration_path'], component_pins=spec['component_sha256'],
                   source_files=installed['source_files'], supervisor={'pid': ready['main_pid'], 'birth_ticks': 1234, 'command_sha256': '3'*64},
                   gtk={'pid': ready['gtk_pid'], 'birth_ticks': 1235, 'command_sha256': '4'*64},
                   camera={'pid': spec['camera_owner']['camera_pid'], 'birth_ticks': int(spec['camera_owner']['camera_start_ticks']),
                           'command_sha256': spec['camera_owner']['camera_cmdline_sha256']},
                   current_publication_committed=True, saved_listening_preference={'version': 1, 'enabled': False},
                   listening={'enabled': False, 'state': 'PAUSED', 'microphone_open': False}, phase='IDLE', playing=False,
                   native_visible=True, native_frames=45, private_data_exported=False,
                   camera_rebind_observation_sha256=spec['camera_rebind']['binding']['written_proof']['observation_sha256'],
                   transaction_sha256=installed['transaction_sha256'])
    raws = {name + '.json': common.encoded(value) for name, value in
            (('spec', spec), ('ready', ready), ('installed', installed))}
    return spec, ready, installed, mapping, raws


class SealTests(unittest.TestCase):
    def setup_paths(self):
        directory = tempfile.TemporaryDirectory(prefix='public-rebind-seal-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        canonical = root / 'canonical'
        canonical.mkdir()
        (canonical / 'spec.json').write_bytes(common.pinned(common.EVIDENCE / 'spec.json', common.BASE_SPEC_SHA))
        (canonical / 'actual_ready.json').write_bytes(common.pinned(common.EVIDENCE / 'ready.json', common.BASE_READY_SHA))
        return canonical, root / 'evidence'

    def test_full_seal_then_retry(self):
        canonical, evidence = self.setup_paths()
        spec, ready, installed, mapping, raws = public_seal_inputs()
        result = seal_rebind.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
        self.assertEqual('CAMERA_REBIND_EVIDENCE_SEALED_CANONICAL_COMMITTED', result['status'])
        self.assertEqual(raws['spec.json'], (canonical / 'spec.json').read_bytes())
        self.assertEqual(raws['ready.json'], (canonical / 'actual_ready.json').read_bytes())
        self.assertTrue((evidence / 'installed.json').exists())
        self.assertEqual(result, seal_rebind.commit_local(raws, mapping, canonical=canonical, evidence=evidence))

    def test_pointer_failure_allows_only_same_transaction_retry(self):
        for point in ('actual_ready.json', 'spec.json'):
            with self.subTest(point=point):
                canonical, evidence = self.setup_paths()
                _, _, _, mapping, raws = public_seal_inputs()
                original = seal_rebind.atomic_file
                def injected(path, raw):
                    original(path, raw)
                    if path.parent == canonical and path.name == point:
                        raise RuntimeError('PUBLIC_POINTER_INTERRUPTION')
                with patch.object(seal_rebind, 'atomic_file', injected), self.assertRaises(RuntimeError):
                    seal_rebind.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
                self.assertTrue((evidence / 'source_mapping.json').exists())
                seal_rebind.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
                self.assertEqual(raws['spec.json'], (canonical / 'spec.json').read_bytes())

    def test_foreign_canonical_is_not_overwritten(self):
        canonical, evidence = self.setup_paths()
        _, _, _, mapping, raws = public_seal_inputs()
        (canonical / 'spec.json').write_bytes(b'PUBLIC_OTHER_RELEASE')
        with self.assertRaisesRegex(ValueError, 'canonical_changed'):
            seal_rebind.commit_local(raws, mapping, canonical=canonical, evidence=evidence)
        self.assertEqual(b'PUBLIC_OTHER_RELEASE', (canonical / 'spec.json').read_bytes())
        self.assertFalse(evidence.exists())

    def test_stale_owner_source_pause_and_incomplete_commit_rejected(self):
        for key in ('owner', 'source', 'pause', 'commit', 'observation', 'transaction'):
            spec, ready, installed, mapping, _ = public_seal_inputs()
            mapping = copy.deepcopy(mapping)
            if key == 'owner':
                mapping['camera']['pid'] = 1335
            elif key == 'source':
                mapping['component_pins']['tools/board_recording.py'] = '9' * 64
            elif key == 'pause':
                mapping['listening']['microphone_open'] = True
            elif key == 'commit':
                mapping['current_publication_committed'] = False
            elif key == 'observation':
                mapping['camera_rebind_observation_sha256'] = '9' * 64
            else:
                mapping['transaction_sha256'] = '9' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                seal_rebind.validate_mapping(mapping, spec, ready, installed)

    def test_mismatched_install_or_ready_rejected(self):
        spec, ready, installed, _, _ = public_seal_inputs()
        installed['changed_component_count'] = 2
        with self.assertRaises(ValueError):
            seal_rebind.validate_inputs(spec, ready, installed)
        _, ready, installed, _, _ = public_seal_inputs()
        ready['physical_microphone_opened'] = True
        with self.assertRaises(ValueError):
            seal_rebind.validate_inputs(spec, ready, installed)

    def test_bool_integer_aliases_do_not_validate_saved_pause(self):
        for group, key, value in [('saved_listening_preference', 'version', True),
                                  ('saved_listening_preference', 'enabled', 0),
                                  ('listening', 'enabled', 0), ('listening', 'microphone_open', 0)]:
            spec, ready, installed, mapping, _ = public_seal_inputs()
            mapping[group][key] = value
            with self.subTest(group=group, key=key), self.assertRaises(ValueError):
                seal_rebind.validate_mapping(mapping, spec, ready, installed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
