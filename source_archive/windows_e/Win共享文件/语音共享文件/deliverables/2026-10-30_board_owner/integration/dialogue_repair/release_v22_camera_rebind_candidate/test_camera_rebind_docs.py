"""Read-only document regression checks against sealed v22 metadata."""
import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import update_camera_rebind_docs as docs


FOLLOW = docs.REPAIR / 'progress_followup_20261031'
ARGUMENTS = (
    FOLLOW / 'v22_features_live_1793509494534555400.json',
    '6405e83afc4e5c356b05d03318366b40d19ef8caebbdbc17a91430678b9740af',
    FOLLOW / 'v22_display_observe_1793509425188329800.json',
    'cc4d4e5e23f17e0828beb6da82279565807ffd1c259468e6fc8ab627df3b6e7b',
)


class CameraRebindDocsTests(unittest.TestCase):
    def setUp(self):
        self.bundle = docs.read_bundle(*ARGUMENTS)

    def test_twelve_targets_and_exact_current_owners(self):
        plan = docs.build_plan(self.bundle)
        value = plan['observation']
        self.assertEqual(12, len(plan['updates']))
        self.assertEqual(docs.STARTUP, value['startup_sha256'])
        self.assertEqual((229842, 229850, 229296), (value['supervisor_pid'], value['gtk_pid'], value['camera_pid']))
        self.assertEqual(380, value['component_pins'])
        self.assertEqual(['config/board_avatar_gtk.json'], list(value['source_files']))
        self.assertIs(value['listening']['enabled'], False)
        self.assertEqual(2, value['frontend_options']['asr_threads'])
        self.assertEqual(1, value['frontend_options']['frontend_threads'])

    def test_old_full_display_period_and_current_probe_remain_separate(self):
        value = docs.build_plan(self.bundle)['observation']
        previous, current = value['historical_v21_display_full_period'], value['display_finalization']
        self.assertNotEqual(previous['startup_sha256'], current['startup_sha256'])
        self.assertEqual(651, previous['samples'])
        self.assertEqual(31, current['samples'])
        self.assertEqual(4928, current['max_idle_ms'])
        self.assertEqual(0, current['observer_reset_calls'])
        self.assertIs(current['physical_panel_observed'], False)
        self.assertIs(current['first_probe_failure_preserved'], True)
        self.assertNotIn('owners', previous)

    def test_worker_absence_and_current_negation_reason_are_explicit(self):
        value = docs.build_plan(self.bundle)['observation']
        self.assertEqual({'available': False}, value['renderer_worker_faults'])
        self.assertIs(value['worker_fault_probe_correction']['worker_fault_absence_verified'], False)
        memory = value['memory']
        self.assertEqual(45, memory['worker']['completed'])
        self.assertEqual(5, memory['worker']['discarded'])
        self.assertEqual(['negation_missing'], memory['current_diagnosis']['summary']['rejection_reasons'])
        self.assertIs(memory['completion_counter_is_not_model_call_count'], True)
        self.assertIs(memory['whole_store_health_verified'], False)

    def test_jpeg_confounding_repeated_A1_and_normal_stop_are_retained(self):
        value = docs.build_plan(self.bundle)['observation']
        jpeg = value['jpeg_actual_ABA']
        self.assertIs(jpeg['causal_CPU_savings_established'], False)
        self.assertIs(jpeg['A1_repeated_preserved'], True)
        self.assertIs(jpeg['B_permanently_adopted'], False)
        self.assertIs(jpeg['stop_refusal_preserved'], True)
        self.assertIs(jpeg['finalize_complete'], True)
        self.assertIs(jpeg['forced_kill'], False)

    def test_historical_tests_cleanup_and_physical_gaps_remain(self):
        value = docs.build_plan(self.bundle)['observation']
        self.assertEqual('v20', value['arm_public_validation']['revision_when_executed'])
        self.assertEqual(92, value['arm_public_validation']['tests'])
        self.assertEqual(2, len(value['legacy_collection_gap']['modules']))
        self.assertEqual(11, value['public_test_cleanup']['total_directories'])
        self.assertIs(value['current_revision_acceptance']['physical_audio_acceptance_passed'], False)
        self.assertIs(value['windows_inference_health']['tts_ready'], True)
        self.assertEqual(16, value['windows_inference_health']['num_step'])

    def test_unrequested_listening_old_boot_or_old_snapshot_refuse(self):
        for field, replacement in [('startup_sha256', '0' * 64), ('board_boot_id', 'other'), ('observed_mono', 1)]:
            value = copy.deepcopy(self.bundle['observed'])
            value[field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                docs.validate_observation(value, self.bundle)
        value = copy.deepcopy(self.bundle['observed'])
        value['listening']['enabled'] = True
        with self.assertRaises(ValueError):
            docs.validate_observation(value, self.bundle)

    def test_wrong_display_owner_policy_or_clock_refuse(self):
        for change in ('owner', 'policy', 'clock', 'observer'):
            value = copy.deepcopy(self.bundle['display'])
            if change == 'owner':
                value['owners']['camera']['pid'] = 1335
            elif change == 'policy':
                value['samples'][0]['screen_saver']['timeout'] = 0
            elif change == 'clock':
                value['observed_mono'] = self.bundle['observed']['observed_mono'] + 1
            else:
                value['observer_reset_calls'] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                docs.validate_display(value, self.bundle)

    def test_missing_final_observations_do_not_plan_or_write(self):
        value = copy.deepcopy(self.bundle)
        value['observed'] = None
        with self.assertRaisesRegex(ValueError, 'final_runtime_and_display'):
            docs.build_plan(value)
        self.assertFalse(docs.HERE.exists())
        self.assertFalse(docs.CANONICAL_OBSERVATION.exists())

    def test_old_note_suffix_and_current_document_bytes_remain_exact_in_dry_plan(self):
        plan = docs.build_plan(self.bundle)
        old_note = (docs.REPAIR / 'docs_state_v21/current_note.txt').read_bytes()
        for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
            self.assertEqual(plan['originals'][key][len(old_note):],
                             plan['updates'][key][len(plan['note'].encode('utf-8')):])
        for key, path in plan['targets'].items():
            self.assertEqual(plan['originals'][key], path.read_bytes())

    def test_default_cli_is_read_only(self):
        args = ['update_camera_rebind_docs.py', '--observation', str(ARGUMENTS[0]),
                '--observation-sha256', ARGUMENTS[1], '--display', str(ARGUMENTS[2]), '--display-sha256', ARGUMENTS[3]]
        with patch('sys.argv', args), patch.object(docs, 'apply_plan', side_effect=AssertionError('write attempted')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            docs.main()
        self.assertIn('NO_WRITES', output.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
