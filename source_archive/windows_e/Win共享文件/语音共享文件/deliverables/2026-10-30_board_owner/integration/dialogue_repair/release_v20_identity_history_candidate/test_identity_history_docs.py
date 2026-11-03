"""Read-only v20 document planning tests against sealed root evidence."""
import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import update_identity_history_docs as docs


class IdentityHistoryDocsTests(unittest.TestCase):
    def setUp(self):
        self.bundle = docs.read_bundle()

    def test_bound_seal_and_final_snapshot_produce_twelve_paused_documents(self):
        plan = docs.build_plan(self.bundle)
        self.assertEqual(12, len(plan['updates']))
        observation = plan['observation']
        self.assertEqual(docs.EXPECTED_STARTUP, observation['startup_sha256'])
        self.assertEqual(380, observation['component_pins'])
        self.assertIs(observation['listening']['enabled'], False)
        self.assertEqual('暂时保持暂停', observation['latest_user_listening_instruction'])
        self.assertIs(observation['pending']['m03_date_delete_deployed'], True)
        self.assertIs(observation['pending']['speaker_calibrated'], False)
        self.assertIs(observation['current_revision_acceptance']['full_physical_dialogue_acceptance'], False)

    def test_arm_and_known_gaps_are_recorded_without_health_overclaim(self):
        observation = docs.build_plan(self.bundle)['observation']
        self.assertEqual(92, observation['arm_public_validation']['tests'])
        self.assertIs(observation['arm_public_validation']['limits']['model_called'], False)
        self.assertEqual(11, observation['memory']['worker']['completed'])
        self.assertEqual(11, observation['memory']['worker']['discarded'])
        self.assertIs(observation['memory']['specific_failure_reason_available'], False)
        self.assertEqual(2, len(observation['legacy_collection_gap']['modules']))
        self.assertEqual(11, observation['public_test_cleanup']['total_directories'])
        self.assertEqual(10316348, observation['public_test_cleanup']['regular_file_bytes'])

    def test_other_revision_boot_or_unrequested_listening_is_rejected(self):
        for field, value in [('startup_sha256', '0'*64), ('board_boot_id', 'other-boot')]:
            changed = copy.deepcopy(self.bundle['observed'])
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                docs.validate_observation(changed, self.bundle['spec'])
        changed = copy.deepcopy(self.bundle['observed'])
        changed['listening'].update(enabled=True, state='WAITING_SPEECH', microphone_open=True)
        with self.assertRaisesRegex(ValueError, 'explicit_pause'):
            docs.validate_observation(changed, self.bundle['spec'])

    def test_uncommitted_or_superseded_canonical_cannot_update_documents(self):
        raws = self.bundle['raws']
        marker = dict(phase='COMMITTED', spec_sha256=docs.seal.common.sha(raws['spec.json']),
                      ready_sha256=docs.seal.common.sha(raws['ready.json']))
        current = {'spec.json': raws['spec.json'], 'actual_ready.json': raws['ready.json']}
        docs.require_committed(raws, marker, current)
        with self.assertRaises(ValueError):
            docs.require_committed(raws, dict(marker, phase='PREPARED'), current)
        with self.assertRaises(ValueError):
            docs.require_committed(raws, marker, dict(current, **{'spec.json': b'newer-version'}))

    def test_previous_documents_are_unchanged_and_plaintext_history_is_exact(self):
        plan = docs.build_plan(self.bundle)
        for key, path in plan['targets'].items():
            self.assertEqual(plan['originals'][key], path.read_bytes())
        old_note = (docs.REPAIR / 'docs_state_v19/current_note.txt').read_bytes()
        for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
            self.assertEqual(plan['originals'][key][len(old_note):],
                             plan['updates'][key][len(plan['note'].encode('utf-8')):])

    def test_default_cli_does_not_apply(self):
        with patch('sys.argv', ['update_identity_history_docs.py']), \
                patch.object(docs, 'apply_plan', side_effect=AssertionError('write attempted')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            docs.main()
        self.assertIn('NO_WRITES', output.getvalue())


if __name__ == '__main__':
    unittest.main()
