"""Saved-pause and dry-run tests using in-memory state and AST functions."""
import ast
import copy
import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import apply_stability_closed
import publish_stability
import stability_common as common


def fixture():
    path = common.REPAIR / 'release_v17_candidate/test_guard_v16.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'paused_fixture')
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<original-public-paused-fixture>', 'exec'), namespace)
    return namespace['paused_fixture']()


def function_namespace(state, expected=False, disk=False, preference_exists=True):
    source = common.publisher_remote(common.baseline())
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in ('never_armed_paused_capture', 'state', 'ready_state')]

    def need(condition, code):
        if not condition:
            raise ValueError(code)

    namespace = {
        'SPEC': dict(common.baseline(), expected_final_listening_enabled=expected),
        'V18_STAGE': 'response-latency-v18-memory-recall',
        'need': need, 'listening_readonly_state': lambda: state,
        'Path': lambda value: SimpleNamespace(exists=lambda: preference_exists),
        'c': SimpleNamespace(parse=json.loads, read=lambda path: json.dumps({'version': 1, 'enabled': disk})),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<fake-v19-state>', 'exec'), namespace)
    return namespace


class SavedPauseTests(unittest.TestCase):
    def test_baseline_and_proposed_bind_latest_saved_pause(self):
        for spec in (common.baseline(), common.proposed()):
            self.assertIs(spec['expected_final_listening_enabled'], False)
            self.assertEqual(380, len(spec['component_sha256']))

    def test_non_boolean_preference_rejected_locally(self):
        for value in (0, 1, None, 'false'):
            spec = common.proposed()
            spec['expected_final_listening_enabled'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'explicit_boolean'):
                common.validate_spec(spec, allow_proposed=True)

    def test_production_never_armed_pause_is_valid_for_close_and_ready(self):
        value = fixture()
        functions = function_namespace(value)
        self.assertTrue(functions['never_armed_paused_capture'](value))
        self.assertIs(functions['state'](), value)
        self.assertIs(functions['ready_state'](), value)

    def test_remote_expectation_rejects_wrong_value_or_type(self):
        for expected in (True, 0, None, 'false'):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                function_namespace(fixture(), expected=expected)['ready_state']()

    def test_changed_disk_preference_is_not_silently_overridden(self):
        value = fixture()
        value['handsfree_dialogue'].update(enabled=True, state='WAITING_SPEECH', microphone_open=True)
        with self.assertRaisesRegex(ValueError, 'latest_user_listening_preference_required'):
            function_namespace(value, disk=True)['ready_state']()

    def test_missing_preference_cannot_impersonate_explicit_pause(self):
        with self.assertRaises(ValueError):
            function_namespace(fixture(), preference_exists=False)['ready_state']()

    def test_enabled_microphone_or_following_is_rejected(self):
        for section, key, changed in (
            ('handsfree_dialogue', 'enabled', True),
            ('handsfree_dialogue', 'microphone_open', True),
            ('handsfree_dialogue', 'state', 'WAITING_SPEECH'),
            ('manual_pan', 'automatic_following', True),
            ('manual_pan', 'pulse_us', 1500),
        ):
            value = fixture()
            value[section][key] = changed
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                function_namespace(value)['ready_state']()

    def test_ready_only_changes_expected_bool_guard(self):
        before = common.previous_publisher().build_remote(common.baseline())
        after = common.publisher_remote(common.baseline())
        old = " if SPEC['release_stage']==V18_STAGE:need(enabled is True,'latest_user_listening_preference_true_required')"
        replacement = " need(type(SPEC.get('expected_final_listening_enabled')) is bool,'valid_expected_listening_preference_required')\n if SPEC['release_stage']==V18_STAGE:need(enabled is SPEC['expected_final_listening_enabled'],'latest_user_listening_preference_required')"
        expected = common.replace_once(before, old, replacement)
        select = lambda text: next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'ready_state')
        self.assertEqual(ast.dump(select(expected)), ast.dump(select(after)))

    def test_reconstructed_current_startup_matches_d24b0d(self):
        startup = common.previous_publisher().inputs()[1]
        startup['component_sha256'] = common.baseline()['component_sha256']
        self.assertEqual(common.BASE_STARTUP_SHA, common.sha(common.encoded(startup)))

    def test_exact_gtk_and_configuration_payload_rejects_a_subset(self):
        value = json.loads((common.HERE / 'APPROVED_PAYLOAD.json').read_bytes())
        value['sources'].pop('config/board_avatar_gtk.json')
        original = common.pinned

        def substitute(path, expected):
            if Path(path).name == 'APPROVED_PAYLOAD.json':
                return common.encoded(value)
            return original(path, expected)

        with patch.object(common, 'pinned', side_effect=substitute), self.assertRaisesRegex(ValueError, 'source_paths_required'):
            common.approved_sources()

    def test_default_publication_and_apply_do_not_call_transport(self):
        original = common.pinned
        cases = ((publish_stability, common.baseline(), ['guard']),
                 (apply_stability_closed, common.proposed(), []))
        for module, spec, actions in cases:
            raw = common.encoded(spec)

            def substitute(path, expected):
                if str(path) == 'public-spec.json':
                    self.assertEqual(common.sha(raw), expected)
                    return raw
                return original(path, expected)

            argv = ['public-dry-test', *actions, '--spec', 'public-spec.json', '--spec-sha256', common.sha(raw)]
            with self.subTest(module=module.__name__), patch.object(common, 'pinned', side_effect=substitute), \
                    patch.object(common, 'execute_remote', side_effect=AssertionError('transport called')), \
                    patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()) as output:
                module.main()
            self.assertIn('NO_SSH', output.getvalue())


if __name__ == '__main__':
    unittest.main()
