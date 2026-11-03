"""Read-only verification of the final v24 documentation plan."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import update_final_docs as docs


FOLLOW = docs.REPAIR / 'progress_followup_20261031'
ARGUMENTS = (
    FOLLOW / 'v24_final_quiet_1793520841434956700.json', docs.OBSERVATION_SHA,
    FOLLOW / 'v24_display_observe_1793518997626554800.json', docs.DISPLAY_SHA,
)


class FinalDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = docs.read_bundle(*ARGUMENTS)

    def test_exact_current_release_and_twelve_targets(self):
        plan = docs.build_plan(self.bundle)
        value = plan['observation']
        self.assertEqual(12, len(plan['updates']))
        self.assertEqual('v24', value['revision'])
        self.assertEqual(docs.STARTUP, value['startup_sha256'])
        self.assertEqual((330179, 330183, 229296), (value['supervisor_pid'], value['gtk_pid'], value['camera_pid']))
        self.assertFalse(value['listening']['enabled'])
        self.assertEqual('PAUSED', value['listening']['state'])

    def test_three_count_snapshots_are_separate_from_final_window(self):
        value = docs.build_plan(self.bundle)['observation']
        counts = value['memory_backlog_comparison']
        rows = [counts[key] for key in ('before', 'during_v24', 'after')]
        self.assertEqual([38, 13, 0], [row['pending_user_said_bodies'] for row in rows])
        self.assertEqual([20, 12, 0], [row['pending_assistant_played_bodies'] for row in rows])
        self.assertEqual([33, 14, 0], [row['failed_candidate_tasks_with_pending_bodies'] for row in rows])
        self.assertEqual([2807, 2826, 2879], [row['committed_summary_count'] for row in rows])
        self.assertTrue(counts['global_summary_count_is_separate_from_final_90_second_window'])
        self.assertNotIn('committed_summary_count', value['runtime_observation_window'])

    def test_final_quiet_has_no_new_model_acceptance_or_rejection(self):
        value = docs.build_plan(self.bundle)['observation']
        window = value['runtime_observation_window']
        self.assertEqual(46, window['samples'])
        self.assertAlmostEqual(90.029197973, window['elapsed_seconds'])
        self.assertEqual([78, 80], window['completed_first_last'])
        self.assertEqual([68, 68], window['discarded_first_last'])
        self.assertEqual([1010, 1010], window['accepted_llm_first_last'])
        self.assertEqual([0, 0], window['pending_failed_tasks_first_last'])
        self.assertEqual([0], window['failure_streak_values'])
        self.assertFalse(window['new_rejections_observed'])
        self.assertIsNone(value['runtime_observed_mono'])
        self.assertFalse(window['absolute_monotonic_timestamps_available'])
        self.assertFalse(value['memory']['whole_store_health_verified'])
        self.assertFalse(value['memory']['multi_hour_summary_stability_verified'])

    def test_visibility_dips_and_missing_worker_metadata_remain_explicit(self):
        plan = docs.build_plan(self.bundle)
        value = plan['observation']
        window = value['runtime_observation_window']
        self.assertEqual(6, window['native_visibility_false_samples'])
        self.assertTrue(window['first_and_final_native_visible'])
        self.assertIn('6点曾为false', plan['note'])
        self.assertEqual([5184, 5440], window['visual_steps_first_last'])
        self.assertFalse(value['worker_fault_probe_correction']['worker_fault_absence_verified'])

    def test_old_failures_and_retry_observation_are_historical(self):
        value = docs.build_plan(self.bundle)['observation']
        prior = self.bundle['fixed']['current_observation_v24.json']
        self.assertEqual([1, 9], prior['runtime_observation_window']['discarded_first_last'])
        self.assertTrue(prior['memory']['summary_rejection_stability_unresolved'])
        self.assertFalse(value['memory']['summary_rejection_stability_unresolved'])
        history = value['historical_v24_retry_observation']
        self.assertEqual(6, history['observed_repeat_interval_count'])
        self.assertEqual((3, 0), (history['samples'][0]['pending_failed_tasks_observed'], history['samples'][-1]['pending_failed_tasks_observed']))
        self.assertEqual('PENDING', value['public_summary_validation']['human_signoff'])

    def test_offline_v25_and_existing_acceptance_limits_remain(self):
        value = docs.build_plan(self.bundle)['observation']
        offline = value['offline_v25_retry_candidate']
        self.assertEqual('OFFLINE_CANDIDATE_NOT_DEPLOYED', offline['status'])
        self.assertFalse(offline['execution_enabled'])
        self.assertFalse(offline['actual_spec_generated'])
        self.assertEqual(27, offline['candidate_public_tests_passed'])
        self.assertFalse(value['speaker']['speaker_calibrated'])
        self.assertFalse(value['current_revision_acceptance']['physical_audio_acceptance_passed'])
        self.assertEqual('FAULT/null', value['retained_mechanical_boundary']['required_state'])
        self.assertFalse(value['retained_mechanical_boundary']['tracking_enabled'])
        self.assertFalse(value['jpeg_actual_ABA']['B_permanently_adopted'])

    def test_changed_quiet_evidence_refuses(self):
        original = json.loads(ARGUMENTS[0].read_bytes())
        for field, bad in (('pending_failed_tasks_observed', 1), ('accepted_llm_total', 1011),
                           ('memory_error_present', True), ('worker_discarded', 69), ('inference_active', True)):
            value = copy.deepcopy(original)
            value['samples'][12][field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                docs.validate_observation(value, self.bundle['spec'], self.bundle['mapping'])
        value = copy.deepcopy(original)
        value['full_380_and_same_owners_before_after'] = False
        with self.assertRaises(ValueError):
            docs.validate_observation(value, self.bundle['spec'], self.bundle['mapping'])

    def test_display_owner_and_original_policy_remain_guarded(self):
        value = copy.deepcopy(self.bundle['display'])
        value['samples'][0]['screen_saver']['timeout'] = 0
        with self.assertRaises(ValueError):
            docs.validate_display(value, self.bundle['spec'], self.bundle['mapping'])

    def test_history_and_frozen_publisher_bytes_unchanged(self):
        plan = docs.build_plan(self.bundle)
        old = (docs.REPAIR / 'docs_state_v24/current_note.txt').read_bytes()
        for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
            self.assertEqual(plan['originals'][key][len(old):], plan['updates'][key][len(plan['note'].encode()):])
        for folder, handoff in (('release_v24_memory_followup_candidate', 'HANDOFF.json'),
                                ('release_v25_memory_retry_candidate', 'DRAFT_HANDOFF.json')):
            path = docs.REPAIR / folder
            frozen = json.loads((path / handoff).read_bytes())
            for name, row in frozen['files'].items():
                self.assertEqual(row['sha256'], docs.seal.common.sha((path / name).read_bytes()))
        self.assertFalse(docs.HERE.exists())
        self.assertFalse(docs.CURRENT.exists())

    def test_default_cli_is_read_only(self):
        arguments = ['update_final_docs.py', '--observation', str(ARGUMENTS[0]),
            '--observation-sha256', ARGUMENTS[1], '--display', str(ARGUMENTS[2]), '--display-sha256', ARGUMENTS[3]]
        with patch('sys.argv', arguments), patch.object(docs, 'apply_plan', side_effect=AssertionError('write attempted')), contextlib.redirect_stdout(io.StringIO()) as output:
            docs.main()
        self.assertIn('NO_WRITES', output.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
