"""Read-only checks for v24 continuation entries and truthful scope."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import update_followup_docs as docs


FOLLOW = docs.REPAIR / 'progress_followup_20261031'
ARGUMENTS = (
    FOLLOW / 'v24_live_observe_1793519187600802100.json', docs.OBSERVATION_SHA,
    FOLLOW / 'v24_display_observe_1793518997626554800.json', docs.DISPLAY_SHA,
)


class FollowupDocsTests(unittest.TestCase):
    def setUp(self):
        self.bundle = docs.read_bundle(*ARGUMENTS)

    def test_twelve_targets_match_actual_one_policy_release(self):
        plan = docs.build_plan(self.bundle)
        value = plan['observation']
        self.assertEqual(12, len(plan['updates']))
        self.assertEqual(docs.PRODUCTS, value['source_files'])
        self.assertEqual(docs.STARTUP, value['startup_sha256'])
        self.assertEqual((330179, 330183, 229296), (value['supervisor_pid'], value['gtk_pid'], value['camera_pid']))
        self.assertEqual(380, value['component_pins'])

    def test_production_rejections_remain_open_despite_public_pass(self):
        plan = docs.build_plan(self.bundle)
        value = plan['observation']
        memory = value['memory']
        self.assertEqual((19, 9), (memory['worker']['completed'], memory['worker']['discarded']))
        self.assertEqual(['negation_missing'], memory['current_diagnosis']['summary']['rejection_reasons'])
        self.assertTrue(memory['summary_rejection_stability_unresolved'])
        self.assertFalse(memory['whole_store_health_verified'])
        self.assertFalse(memory['multi_hour_summary_stability_verified'])
        self.assertTrue(memory['original_source_retained_until_successful_validated_summary'])
        self.assertIn('真实数据仍有校验拒绝', plan['note'])
        self.assertIn('negation_missing', plan['updates']['project_README'].decode())

    def test_window_counts_are_same_process_and_worker_faults_unavailable(self):
        value = docs.build_plan(self.bundle)['observation']
        window = value['runtime_observation_window']
        self.assertEqual(181, window['samples'])
        self.assertEqual([8, 19], window['completed_first_last'])
        self.assertEqual([1, 9], window['discarded_first_last'])
        self.assertEqual([0, 1, 2, 3, 4], window['failure_streak_values'])
        self.assertEqual([207, 747], window['visual_steps_first_last'])
        self.assertFalse(value['worker_fault_probe_correction']['worker_fault_absence_verified'])
        self.assertEqual({'available': False}, value['renderer_worker_faults'])

    def test_backlog_counts_keep_user_and_assistant_scopes_separate(self):
        plan = docs.build_plan(self.bundle)
        comparison = plan['observation']['memory_backlog_comparison']
        before, after = comparison['before'], comparison['during_v24']
        self.assertEqual((38, 13), (before['pending_user_said_bodies'], after['pending_user_said_bodies']))
        self.assertEqual((20, 12), (before['pending_assistant_played_bodies'], after['pending_assistant_played_bodies']))
        self.assertEqual((33, 14), (before['failed_candidate_tasks_with_pending_bodies'], after['failed_candidate_tasks_with_pending_bodies']))
        self.assertEqual((2807, 2826), (before['committed_summary_count'], after['committed_summary_count']))
        self.assertFalse(comparison['all_pending_bodies_cleared'])
        self.assertFalse(comparison['failed_groups_cleared'])
        self.assertIn('待处理用户原文38→13', plan['note'])

    def test_public_review_is_assistant_and_raw_human_pending(self):
        value = docs.build_plan(self.bundle)['observation']['public_summary_validation']
        self.assertEqual((11, 15, 16, 301), (value['before_accepted'], value['after_accepted'], value['actual_llm_calls'], value['capacity_utf8_bytes']))
        self.assertEqual(['root_assistant', 'independent_assistant'], value['reviewers'])
        self.assertEqual('PENDING', value['human_signoff'])
        self.assertEqual(2, value['long_record_source_fragments'])
        self.assertEqual(0, value['long_record_reduction_rounds'])
        raw = self.bundle['fixed'][docs.VALIDATION + 'ACTUAL_CANDIDATE_R2_ALL_1793518296885058600.json']
        self.assertTrue(all(row['human_semantic_review'] == 'PENDING' for row in raw['result']['cases']))

    def test_display_and_old_scope_remain_separate(self):
        value = docs.build_plan(self.bundle)['observation']
        display = value['display_finalization']['observation']
        self.assertEqual((31, 6, 4857), (len(display['samples']), display['idle_drop_count'], display['max_idle_ms']))
        self.assertTrue(value['display_finalization']['external_input_not_excluded'])
        self.assertFalse(value['display_finalization']['physical_panel_observed'])
        self.assertEqual(651, value['historical_v21_display_full_period']['samples'])
        self.assertEqual('v22', value['windows_inference_health']['revision_when_observed'])
        self.assertEqual('v20', value['arm_public_validation']['revision_when_executed'])
        self.assertFalse(value['current_revision_acceptance']['actual_arm_public_synthetic_tests_passed'])

    def test_audio_preference_and_existing_feature_gaps_preserved(self):
        value = docs.build_plan(self.bundle)['observation']
        self.assertFalse(value['listening']['enabled'])
        self.assertEqual(2, value['frontend_options']['asr_threads'])
        self.assertEqual(1, value['frontend_options']['frontend_threads'])
        self.assertFalse(value['speaker']['speaker_calibrated'])
        self.assertFalse(value['current_revision_acceptance']['physical_audio_acceptance_passed'])
        self.assertFalse(value['jpeg_actual_ABA']['B_permanently_adopted'])
        self.assertEqual(11, value['public_test_cleanup']['total_directories'])
        self.assertEqual(2, len(value['legacy_collection_gap']['modules']))

    def test_wrong_live_boot_pause_clock_or_mapping_refuses(self):
        raw = json.loads(ARGUMENTS[0].read_bytes())
        for field in ('boot', 'pause', 'clock', 'mapping'):
            value = copy.deepcopy(raw)
            if field == 'boot':
                value['boot_id'] = 'other'
            elif field == 'pause':
                value['samples'][12]['listening']['enabled'] = True
            elif field == 'clock':
                value['samples'][0]['observed_mono'] = 1
            else:
                value['source_mapping_sha256'] = '0' * 64
            with self.subTest(field=field), self.assertRaises(Exception):
                docs.validate_observation(value, self.bundle['spec'], self.bundle['mapping'])

    def test_wrong_display_owner_policy_or_observer_refuses(self):
        for field in ('owner', 'policy', 'observer'):
            value = copy.deepcopy(self.bundle['display'])
            if field == 'owner':
                value['owners']['camera']['pid'] = 1335
            elif field == 'policy':
                value['samples'][0]['screen_saver']['timeout'] = 0
            else:
                value['observer_reset_calls'] = 1
            with self.subTest(field=field), self.assertRaises(Exception):
                docs.validate_display(value, self.bundle['spec'], self.bundle['mapping'])

    def test_old_note_suffix_and_original_twelve_bytes_unchanged(self):
        plan = docs.build_plan(self.bundle)
        old = (docs.REPAIR / 'docs_state_v23/current_note.txt').read_bytes()
        for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
            self.assertEqual(plan['originals'][key][len(old):], plan['updates'][key][len(plan['note'].encode()):])
        for key, path in plan['targets'].items():
            self.assertEqual(plan['originals'][key], path.read_bytes())
        self.assertFalse(docs.HERE.exists())
        self.assertFalse(docs.CURRENT.exists())

    def test_frozen_execution_package_and_historical_docs_are_unchanged(self):
        package = docs.seal.common.HERE
        handoff = json.loads((package / 'HANDOFF.json').read_bytes())
        self.assertEqual(17, len(handoff['files']))
        for name, item in handoff['files'].items():
            self.assertEqual(item['sha256'], docs.seal.common.sha((package / name).read_bytes()))
        previous = json.loads(docs.seal.common.pinned(docs.PRIOR, docs.FIXED['docs_state_v23/HANDOFF.json']))
        for item in previous['changed_documents']:
            self.assertEqual(item['sha256'], docs.seal.common.sha(Path(item['path']).read_bytes()))

    def test_default_cli_is_read_only(self):
        arguments = ['update_followup_docs.py', '--observation', str(ARGUMENTS[0]),
            '--observation-sha256', ARGUMENTS[1], '--display', str(ARGUMENTS[2]), '--display-sha256', ARGUMENTS[3]]
        with patch('sys.argv', arguments), patch.object(docs, 'apply_plan', side_effect=AssertionError('write attempted')), contextlib.redirect_stdout(io.StringIO()) as output:
            docs.main()
        self.assertIn('NO_WRITES', output.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
