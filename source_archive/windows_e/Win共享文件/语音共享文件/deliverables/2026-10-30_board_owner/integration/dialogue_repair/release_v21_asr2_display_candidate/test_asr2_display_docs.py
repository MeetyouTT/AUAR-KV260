"""Read-only v21 documentation checks against locally sealed evidence."""
import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import update_asr2_display_docs as docs


class AsrDisplayDocsTests(unittest.TestCase):
    def setUp(self):
        self.bundle = docs.read_bundle()

    def observation_fixture(self):
        return {
            'startup_sha256': docs.EXPECTED_STARTUP,
            'board_boot_id': self.bundle['spec']['boot_id'],
            'observed_mono': self.bundle['mapping']['observed_mono'] + 1,
            'phase': 'IDLE',
            'playing': False,
            'listening': {'enabled': False, 'state': 'PAUSED', 'microphone_open': False},
        }

    def test_actual_two_component_seal_produces_twelve_paused_documents(self):
        plan = docs.build_plan(self.bundle)
        self.assertEqual(12, len(plan['updates']))
        observation = plan['observation']
        self.assertEqual(docs.EXPECTED_STARTUP, observation['startup_sha256'])
        self.assertEqual(380, observation['component_pins'])
        self.assertEqual(2, len(observation['source_files']))
        self.assertIs(observation['listening']['enabled'], False)
        self.assertEqual('暂时保持暂停', observation['latest_user_listening_instruction'])
        self.assertIs(observation['current_revision_acceptance']['full_physical_dialogue_acceptance'], False)
        self.assertEqual(2, observation['frontend_options']['asr_threads'])
        self.assertEqual(1, observation['frontend_options']['frontend_threads'])

    def test_historical_arm_and_current_memory_gaps_remain_distinct(self):
        observation = docs.build_plan(self.bundle)['observation']
        arm = observation['arm_public_validation']
        self.assertEqual('v20', arm['revision_when_executed'])
        self.assertEqual(92, arm['tests'])
        self.assertIs(arm['carried_function_source_pins_still_match'], True)
        self.assertIs(arm['limits']['model_called'], False)
        self.assertIs(observation['memory']['current_runtime_available'], True)
        self.assertEqual(2, observation['memory']['worker']['completed'])
        self.assertEqual(35, observation['memory']['worker']['discarded'])
        self.assertEqual(19, observation['memory']['retry']['failure_streak'])
        self.assertIs(observation['memory']['whole_store_health_verified'], False)
        self.assertEqual(2, len(observation['legacy_collection_gap']['modules']))
        self.assertEqual(11, observation['public_test_cleanup']['total_directories'])
        self.assertEqual(10316348, observation['public_test_cleanup']['regular_file_bytes'])

    def test_v20_function_source_drift_is_rejected(self):
        changed = copy.deepcopy(self.bundle)
        previous = docs.load(docs.REPAIR / 'current_observation_v20.json')
        component = next(iter(previous['source_files']))
        changed['mapping']['component_pins'][component] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'six_source_pins'):
            docs.build_plan(changed)

    def test_public_performance_scope_and_failed_candidate_are_preserved(self):
        performance = docs.performance_evidence()
        asr, frontend = performance['asr'], performance['frontend']
        self.assertEqual(2, asr['public_cases'])
        self.assertEqual(8, asr['timed_samples_total'])
        self.assertIs(asr['background_counter_changed'], True)
        self.assertIs(asr['actual_microphone_or_endpoint_latency_measured'], False)
        self.assertIs(asr['causal_whole_system_gain_claimed'], False)
        self.assertIs(asr['first_trial_setup_failure_preserved'], True)
        self.assertEqual(['A2'], frontend['missing_slots'])
        self.assertEqual('pcm_input_queue_overflow', frontend['B2_queue_error'])
        self.assertIs(frontend['deployed'], False)
        self.assertIs(frontend['complete_ABBA'], False)
        self.assertEqual(1, frontend['production_threads'])
        self.assertEqual(8, frontend['raw_input_queue_frames'])

    def test_missing_b2_overflow_evidence_is_rejected(self):
        real_load = docs.load

        def changed_load(path):
            value = real_load(path)
            if path == docs.FRONTEND_REVIEW:
                value['rows'][2]['queue_error'] = None
            return value

        with patch.object(docs, 'load', side_effect=changed_load):
            with self.assertRaisesRegex(ValueError, 'B2_failure'):
                docs.performance_evidence()

    def test_asr_independent_review_must_bind_actual_evidence(self):
        real_load = docs.load

        def changed_load(path):
            value = real_load(path)
            if path == docs.ASR_REVIEW:
                value['sources'][docs.ASR_ACTUAL.name] = '0' * 64
            return value

        with patch.object(docs, 'load', side_effect=changed_load):
            with self.assertRaisesRegex(ValueError, 'asr_pilot_evidence'):
                docs.performance_evidence()

    def test_other_revision_boot_or_unrequested_listening_is_rejected(self):
        for field, value in [('startup_sha256', '0' * 64), ('board_boot_id', 'other-boot')]:
            changed = self.observation_fixture()
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                docs.validate_observation(changed, self.bundle['spec'])
        changed = self.observation_fixture()
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

    def test_history_bytes_remain_exact_and_draft_apply_is_blocked(self):
        plan = docs.build_plan(self.bundle)
        old_note = (docs.REPAIR / 'docs_state_v20/current_note.txt').read_bytes()
        for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
            self.assertEqual(plan['originals'][key][len(old_note):],
                             plan['updates'][key][len(plan['note'].encode('utf-8')):])
        pending_bundle = copy.deepcopy(self.bundle)
        pending_bundle.update(observed=None, observation_path=None)
        pending_plan = docs.build_plan(pending_bundle)
        with self.assertRaisesRegex(ValueError, 'final_screen_policy_jpeg_and_runtime'):
            docs.apply_plan(pending_plan)
        self.assertFalse(docs.HERE.exists())
        self.assertFalse(plan['canonical'].exists())
        for key, path in plan['targets'].items():
            self.assertEqual(plan['originals'][key], path.read_bytes())

    def test_final_display_and_JPEG_evidence_keep_measured_scope(self):
        observation = docs.build_plan(self.bundle)['observation']
        display = observation['display_finalization']
        self.assertIs(observation['finalization_ready'], True)
        self.assertIs(display['original_X_policy_restored'], True)
        self.assertEqual(31, display['samples'])
        self.assertEqual(6, display['idle_drops'])
        self.assertIs(display['external_input_not_excluded'], True)
        self.assertIs(display['ten_minute_physical_acceptance'], False)
        self.assertIs(observation['jpeg_public_screen']['production_deployed'], False)
        self.assertIs(observation['jpeg_public_screen']['whole_board_CPU_gain_measured'], False)
        self.assertEqual(25524, observation['native']['frames'])
        self.assertIs(observation['physical_screen_frame_rate_measured'], False)

    def test_final_runtime_must_follow_display_restore(self):
        changed = copy.deepcopy(self.bundle)
        changed['observed']['observed_mono'] = changed['mapping']['observed_mono']
        with self.assertRaisesRegex(ValueError, 'follow_display_restoration'):
            docs.build_plan(changed)

    def test_default_cli_does_not_apply(self):
        with patch('sys.argv', ['update_asr2_display_docs.py']), \
                patch.object(docs, 'apply_plan', side_effect=AssertionError('write attempted')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            docs.main()
        self.assertIn('NO_WRITES', output.getvalue())


if __name__ == '__main__':
    unittest.main()
