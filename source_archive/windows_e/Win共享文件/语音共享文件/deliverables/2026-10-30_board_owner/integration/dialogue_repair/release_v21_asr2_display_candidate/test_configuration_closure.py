"""Public source/configuration closure tests for the v21 publisher."""
import ast
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import apply_stability_closed as apply
import stability_common as common


def functions(source):
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def literal(source, name):
    return ast.literal_eval(next(node.value for node in ast.parse(source).body
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name))


class ConfigurationClosureTests(unittest.TestCase):
    def test_only_one_gtk_source_and_one_gui_configuration_change(self):
        before, after = common.baseline(), common.proposed()
        expected = {'tools/board_avatar_gtk.py', 'config/board_avatar_gtk.json'}
        self.assertEqual(common.ALLOWED_PATHS, expected)
        self.assertEqual(len(before['component_sha256']), 380)
        self.assertEqual(len(after['component_sha256']), 380)
        self.assertEqual(set(before['component_sha256']), set(after['component_sha256']))
        self.assertEqual(expected, {name for name, pin in before['component_sha256'].items()
                                   if after['component_sha256'][name] != pin})

    def test_gui_only_changes_asr_three_to_two(self):
        before, after = common.configuration_pair()
        expected = copy.deepcopy(before)
        self.assertEqual(before['board_business']['asr_threads'], 3)
        expected['board_business']['asr_threads'] = 2
        self.assertEqual(expected, after)
        self.assertEqual(after['board_business']['frontend_threads'], 1)
        self.assertEqual(after['board_business']['capture_priority_nice'], -10)

    def test_unrelated_gui_change_is_rejected_even_with_mocked_file_reads(self):
        original = common.pinned
        def changed(path, fingerprint):
            raw = original(path, fingerprint)
            if Path(path) == common.HERE / 'payload' / common.CONFIG_RELATIVE:
                value = json.loads(raw)
                value['board_business']['timeout_ms'] += 1
                return common.encoded(value)
            return raw
        with patch.object(common, 'pinned', changed), self.assertRaisesRegex(ValueError, 'only_asr_threads'):
            common.configuration_pair()

    def test_actual_startup_uses_original_component_configuration_binding(self):
        baseline, proposal = common.baseline(), common.proposed()
        old = common.startup_for(baseline)
        new = common.startup_for(proposal)
        self.assertEqual(set(old), set(new))
        self.assertEqual({key: value for key, value in old.items() if key != 'component_sha256'},
                         {key: value for key, value in new.items() if key != 'component_sha256'})
        self.assertEqual(new['component_sha256'][common.CONFIG_RELATIVE], common.NEW_CONFIG_SHA)
        self.assertEqual(common.sha(common.encoded(old)), common.BASE_STARTUP_SHA)
        self.assertEqual(common.sha(common.encoded(new)), proposal['startup_sha256'])
        self.assertEqual(proposal['configuration_sha256'], common.NEW_CONFIG_SHA)

    def test_new_gui_and_startup_literals_follow_each_phase(self):
        for spec, expected in ((common.baseline(), common.configuration_pair()[0]),
                               (common.proposed(), common.configuration_pair()[1])):
            source = common.publisher_remote(spec)
            self.assertEqual(literal(source, 'EXPECTED_GUI'), expected)
            self.assertEqual(literal(source, 'EXPECTED_STARTUP'), common.startup_for(spec))
            ast.parse(source, feature_version=(3, 9))
        ast.parse(apply.build_remote(common.proposed()), feature_version=(3, 9))

    def test_original_lifecycle_and_legacy_config_anchor_are_preserved(self):
        spec = common.baseline()
        old = common.previous_publisher().build_remote(spec)
        new = common.publisher_remote(spec)
        before, after = functions(old), functions(new)
        for name in ('guard', 'window', 'close', 'start', 'ready', 'inactive', 'boot', 'state', 'never_armed_paused_capture'):
            self.assertEqual(ast.dump(before[name], include_attributes=False),
                             ast.dump(after[name], include_attributes=False), name)
        self.assertEqual(literal(old, 'CONFIG_SHA'), literal(new, 'CONFIG_SHA'))

    def test_source_checks_both_external_reference_and_runtime_configuration(self):
        source = common.publisher_remote(common.proposed())
        text = ast.get_source_segment(source, functions(source)['source'])
        self.assertIn("manifest['configuration_sha256']==SPEC['configuration_sha256']", text)
        self.assertIn("manifest['configuration_path']==SPEC['minor_prepared_configuration_path']", text)
        self.assertIn("c.read(manifest['configuration_path'],SPEC['configuration_sha256'])", text)
        self.assertIn("runtime/aura/config/board_avatar_gtk.json", text)

    def test_original_four_database_bootstrap_and_three_leases_precede_stage(self):
        source = apply.APPLY_REMOTE
        self.assertIn('for rel,pin in BASE_PINS.items():c.read', source)
        self.assertIn("private/'writer.lock',private/'speaker/speaker-writer.lock'", source)
        self.assertLess(source.index('fcntl.flock(stream'), source.index('proof=verify_production_bootstrap'))
        self.assertLess(source.index('proof=verify_production_bootstrap'), source.index('stage.mkdir'))
        self.assertIn("j.get('phase')=='NORMAL_CLOSED'", source)
        self.assertIn("c.show()['ActiveState']=='inactive'", source)

    def test_old_external_configuration_is_only_read_and_backed_up(self):
        source = apply.APPLY_REMOTE
        self.assertIn("old_external_gui=c.read(old_configuration_path,BASE_CONFIG_SHA)", source)
        self.assertIn("c.create(backup/'external-gui-config.json',old_external_gui)", source)
        self.assertIn("c.create(backup/'configuration-paths.json'", source)
        self.assertIn("c.read(old_configuration_path,BASE_CONFIG_SHA)==old_external_gui,'original_configuration_provenance_modified'", source)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args and isinstance(node.func, ast.Name) and node.func.id == 'atomic':
                self.assertNotEqual(ast.unparse(node.args[0]), 'old_configuration_path')

    def test_backups_and_prepared_configuration_are_durable_before_install(self):
        source = apply.APPLY_REMOTE
        first_write = source.index("for rel,raw in new_files.items():atomic(root/'runtime/aura'/rel,raw)")
        for needle in ("c.create(backup/name,raw)", "c.create(destination,original)",
                       "c.create(backup/'external-gui-config.json'", "c.create(stage/'prepared-gui.json'",
                       "c.create(stage/'prepared-manifest.json'", 'os.fsync(stage_fd)',
                       "phase='MINOR_SOURCE_INSTALL_INTENT'"):
            self.assertLess(source.index(needle), first_write, needle)
        self.assertIn("manifest['configuration_path']=PREPARED_CONFIG_PATH", source)
        self.assertIn("manifest['configuration_sha256']=NEW_CONFIG_SHA", source)

    def test_installed_copies_share_new_bytes(self):
        source = apply.APPLY_REMOTE
        self.assertIn("c.read(root/'runtime/aura'/CONFIG_RELATIVE,NEW_CONFIG_SHA)==new_gui_raw", source)
        self.assertIn("c.read(PREPARED_CONFIG_PATH,NEW_CONFIG_SHA)==new_gui_raw", source)
        self.assertIn('gui_configuration_bytes_unchanged=False', source)
        self.assertIn('previous_configuration_preserved=True', source)

    def test_foreign_configuration_path_or_pin_cannot_enter_publication(self):
        for key, value in (('minor_prepared_configuration_path', '/unrelated/config.json'),
                           ('configuration_sha256', common.BASE_CONFIG_SHA)):
            changed = common.proposed()
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                common.validate_spec(changed, allow_proposed=True)

    def test_proposed_cannot_start_and_actual_manifest_is_required(self):
        proposed = common.proposed()
        common.validate_spec(proposed, allow_proposed=True)
        with self.assertRaises(ValueError):
            common.validate_spec(proposed)
        proposed['minor_state'] = 'APPLIED'
        with self.assertRaises(ValueError):
            common.validate_spec(proposed)
        proposed['source_manifest_sha256'] = 'd' * 64
        common.validate_spec(proposed)

    def test_frozen_spec_round_trip_has_identical_remote_bytes(self):
        value = common.proposed()
        restored = json.loads(common.encoded(value))
        self.assertEqual(common.publisher_remote(value), common.publisher_remote(restored))
        self.assertEqual(apply.build_remote(value), apply.build_remote(restored))

    def test_v20_core_and_audio_source_pins_are_preserved(self):
        old, new = common.baseline()['component_sha256'], common.proposed()['component_sha256']
        for name in ('common/board_production_bootstrap.py', 'board/runtime/board_business.py',
                     'common/board_memory.py', 'tools/board_recording.py', 'tools/board_avatar_worker.py',
                     'board/runtime/audio/board_gtcrn_reuse.py', 'board/runtime/audio/board_pcm_queue.py'):
            self.assertEqual(old[name], new[name], name)


if __name__ == '__main__':
    unittest.main()
