"""Synthetic receipt contracts, prepared but not executed by the author."""
import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name('update_verified_state.py')
spec = importlib.util.spec_from_file_location('verified_document_updater', PATH)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def receipts():
    root = '/home/root/aura-board-business-fixture/metadata-only'
    installed = dict(target=root, startup_sha256='a'*64, source_manifest_sha256='b'*64,
        component_pins=99, automatic_listening=True, retention_enabled=True,
        business_options=dict(frontend_process=True, frontend_optimization='fixture',
                              capture_priority_nice=-10, frontend_threads=1))
    ready = dict(status='PRODUCTION_BOARD_BUSINESS_READY', root=root,
        main_pid=123, gtk_pid=124, data_origin='board', guard_removed=True)
    sample = dict(listening=dict(enabled=True, microphone_open=True),
        diagnostics=dict(error_code='none', capture_state='RECORDING',
            input_queue=dict(capacity_frames=8), audio_frontend=dict(frames=1),
            counters=dict(armed=1)), pan=dict(automatic_following=False, state='FAULT', pulse_us=None),
        business=dict(started=True, closed=False, writer_held=True, receipt_verified=True),
        character=dict(state='READY', production_selected=True), native=dict(visible=True), playing=False)
    last = copy.deepcopy(sample); last['diagnostics']['audio_frontend']['frames'] = 2
    live = dict(root=root, startup_sha256='a'*64, source_manifest_sha256='b'*64, component_pins=99,
        continuous_capture_passed=True, priority_scope_passed=True,
        physical_microphone_opened=True, raw_audio_saved_or_transferred=False,
        unit=dict(ActiveState='active', MainPID='123'), gtk_pid=124, camera_pid=125,
        board_boot_id='11111111-1111-1111-1111-111111111111', samples=[sample, last])
    return installed, ready, live


class VerifiedStateTests(unittest.TestCase):
    def test_each_gate_requires_actual_boolean_true(self):
        for key in ('continuous_capture_passed', 'priority_scope_passed'):
            for value in (False, None, 1, 'true'):
                installed, ready, live = receipts(); live[key] = value
                with self.assertRaises(updater.ReceiptRejected): updater.validate(installed, ready, live)

    def test_metadata_revision_and_owner_must_match(self):
        for key, value in (('startup_sha256', 'c'*64), ('source_manifest_sha256', 'c'*64),
                           ('gtk_pid', 999), ('root', '/home/root/different-fixture'),
                           ('component_pins', 100)):
            installed, ready, live = receipts(); live[key] = value
            with self.assertRaises(updater.ReceiptRejected): updater.validate(installed, ready, live)

    def test_dynamic_frontend_is_receipt_owned_and_operator_acceptance_stays_pending(self):
        installed, ready, live = receipts()
        value = updater.validate(installed, ready, live)
        self.assertTrue(value['frontend_options']['frontend_process'])
        self.assertEqual(value['startup_sha256'], installed['startup_sha256'])
        self.assertTrue(value['physical_microphone_opened'])
        self.assertFalse(value['physical_audio_acceptance_passed'])
        self.assertFalse(value['operator_asr_acceptance_passed'])
        self.assertFalse(value['operator_playback_acceptance_passed'])
        self.assertFalse(value['listening_policy']['actual_restart_pause_verified'])

    def test_control_disk_roundtrip_does_not_imply_actual_restart(self):
        installed, ready, live = receipts()
        control = dict(root=installed['target'], startup_sha256=installed['startup_sha256'],
            main_pid=123, gtk_pid=124, pause_preference_false_observed=True,
            resume_preference_true_observed=True, cancel_rearm_passed=True,
            synthetic_restart_preference_check_passed=True, actual_restart_pause_verified=True)
        value = updater.validate(installed, ready, live, control)
        policy = value['listening_policy']
        self.assertEqual(policy['explicit_pause_persistence'], 'actual_disk_preference_roundtrip_verified')
        self.assertEqual(policy['cancel_current_turn_rearm'], 'actual_cancel_rearm_verified')
        self.assertTrue(policy['synthetic_restart_preference_check_passed'])
        self.assertFalse(policy['actual_restart_pause_verified'])

    def test_missing_control_flags_do_not_become_passed(self):
        installed, ready, live = receipts()
        value = updater.validate(installed, ready, live)
        self.assertEqual(value['listening_policy']['explicit_pause_persistence'], 'not_verified_in_receipts')
        self.assertEqual(value['listening_policy']['cancel_current_turn_rearm'], 'not_verified_in_receipts')

    def test_previous_current_block_is_retained_as_history(self):
        original = '<!-- '+updater.TAG+' -->\nold public metadata\n<!-- /'+updater.TAG+' -->\nolder history\n'
        result = updater.tagged(original, 'new verified metadata', 'fixture')
        self.assertTrue(result.startswith('<!-- '+updater.TAG+' -->\nnew verified metadata'))
        self.assertIn('old public metadata', result)
        self.assertIn('older history', result)
        self.assertEqual(result.count('<!-- '+updater.TAG+' -->'), 1)


if __name__ == '__main__': unittest.main()
