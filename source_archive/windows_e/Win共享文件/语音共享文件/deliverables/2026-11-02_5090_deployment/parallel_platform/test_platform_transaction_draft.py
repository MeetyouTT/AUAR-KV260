"""Isolated adversarial transaction tests. All owners/files/jobs are synthetic.

No SSH, subprocess, board filesystem, project module or device is used.
The fake original validator proves call ordering, not the real validator itself.
"""
from copy import deepcopy
import json
import unittest

from platform_transaction_draft import (
    Approval, BoardBackendUnavailable, ExecutionNotReady, HoldRequired,
    OutcomeUnknown, ReviewTransaction, StageRejected, sha,
)


def synthetic_binding():
    return {'scope': 'SYNTHETIC_TEST_ONLY',
        'boot_id': '00000000-0000-4000-8000-000000000001',
        'startup_sha256': 'a' * 64,
        'camera_owner': {'pid': 41, 'birth_ticks': 420, 'command_sha256': 'c' * 64},
        'previous_checkpoint_sha256': '0' * 64,
        'source_unit_sha256': 'd' * 64, 'source_manifest_sha256': 'e' * 64,
        'counter_lower_bounds': {'primary_calls': 10, 'primary_period_overruns': 1, 'sface_completed': 3},
        'wide': {'app': 'SIMULATED_WIDE', 'firmware_name': 'SIMULATED_WIDE.bit.bin',
                 'vart_exact': 'SIMULATED_WIDE_VART\n', 'bench_sha256': 'b' * 64}}


class IsolatedFakeBackend:
    simulation_only = True

    def __init__(self, binding):
        self.binding = deepcopy(binding)
        self.owner = deepcopy(binding['camera_owner'])
        self.camera_job = None
        self.actions = []
        self.saved_states = []
        self.stop_complete = False
        self.restore_complete = False
        self.validator_rejects = False
        self.validator_calls = 0
        self.consumed = False
        self.sealed_bytes = []
        self.wide = False
        self.readback_override = {}
        self.guard_override = {}
        self.loader_pending = {}
        self.unknown_loader_launch = False
        self.bad_stop = False
        self.bad_restore_seed = False
        self.id_stop_pending = False
        self.original_document = {'schema': 'aura-native-protection-checkpoint-2',
            'scope': 'final_quiescent_before_native_owner_close',
            'source_unit_sha256': binding['source_unit_sha256'],
            'seed': {'abi_version': 2, 'purpose': 'final_quiescent_business_checkpoint',
                     'checkpoint_kind': 1, 'boot_id': binding['boot_id'], 'source_pid': 41,
                     'source_birth_ticks': 420, 'source_manifest_sha256': binding['source_manifest_sha256'],
                     'fenced': 0, 'captured_mono_ns': 999, 'primary_calls': 17, 'primary_period_overruns': 1,
                     'recovery': [{'attempts': 1, 'faults': 1}, {'attempts': 0, 'faults': 0}]},
            'auxiliary': {'active': 0, 'primary_waiting': 0, 'fenced': 0,
                          'pending_result_tokens': [0, 0, 0], 'sface_counters': {'completed': 5}},
            'previous_kernel_history': {'scope': 'SYNTHETIC_PREDECESSOR_CHAIN'}}
        self.raw = self.encode_checkpoint(self.original_document)

    @staticmethod
    def encode_checkpoint(document):
        # Deliberately noncanonical whitespace: sealing must preserve these bytes.
        return ('  ' + json.dumps(document, indent=3) + '\n\n').encode()

    def persist_simulation_state(self, state):
        self.saved_states.append(deepcopy(state))

    def recheck(self, binding, session):
        result = {'boot_id': binding['boot_id'], 'startup_sha256': binding['startup_sha256'],
                  'gui_main_pid': 0, 'gui_job': None, 'saved_listening': False,
                  'inspection_complete': True, 'motion_or_raw_mem_owners': [],
                  'camera_owner': deepcopy(self.owner), 'camera_job': self.camera_job,
                  'dpu_owners': [deepcopy(self.owner)] if self.owner is not None else [],
                  'camera_shutdown_protection': True}
        result.update(deepcopy(self.guard_override))
        return result

    def read_preflight(self, binding):
        return {'all_source_and_firmware_pins_match': True, 'scope': 'SIMULATION_ONLY'}

    def request_normal_camera_stop_once(self, intent):
        self.actions.append('NORMAL_STOP_REQUEST')

    def observe_camera_stop(self, intent):
        if not self.stop_complete:
            return {'status': 'PENDING'}
        self.owner = None
        return {'status': 'SUCCESS', 'original_owner_gone': True, 'unit_main_pid': 0,
                'unit_job': None, 'unit_result': 'success', 'exec_main_status': 0}

    def read_actual_checkpoint(self):
        return {'path': '/SIMULATED/checkpoint.json', 'exact_bytes': self.raw,
                'captured_after_stop_intent': True, 'capture_in_current_monotonic_domain': True,
                'previous_kernel_archive_chain_verified': True}

    def call_original_load_business_checkpoint(self, pin, boot):
        self.validator_calls += 1
        if self.validator_rejects:
            raise ValueError('SIMULATED_ORIGINAL_VALIDATOR_REJECTION')
        document = json.loads(self.raw)
        return {'sha256': sha(self.raw), 'document': document,
                'seed': document['seed'], 'auxiliary': document['auxiliary']}

    def checkpoint_still_exact_and_unconsumed(self, pin):
        return pin['sha256'] == sha(self.raw) and not self.consumed

    def seal_exact_original_bytes_once(self, raw, pin, intent):
        self.actions.append('SEAL_REAL_BYTES')
        self.sealed_bytes.append(raw)
        return {'created_exclusively': True, 'readback_sha256': sha(raw),
                'path': '/SIMULATED/session/checkpoint.sealed.json'}

    def launch_loader_once(self, action, intent):
        self.actions.append(action)
        if self.unknown_loader_launch:
            raise OutcomeUnknown('SIMULATED_SSH_LOST_AFTER_INTENT')
        return {'scope': 'SIMULATION_ONLY', 'job_id': 'SIM:' + action}

    def reconcile_loader_readonly(self, action, intent, job):
        if self.loader_pending.get(action, 0) > 0:
            self.loader_pending[action] -= 1
            return {'status': 'PENDING'}
        r = {'status': 'SUCCESS', 'wrapper_returncode': 0,
             'actual_client_identity_verified': True, 'actual_client_exit_code': 0,
             'fresh_readback_verified': True, 'active_application': None}
        if action == 'PL_LOAD_WIDE':
            w = self.binding['wide']
            self.wide = True
            r.update(boot_id=self.binding['boot_id'], active_application=w['app'],
                     firmware_name=w['firmware_name'], fpga_state='operating', vart_exact=w['vart_exact'],
                     all_runtime_and_driver_pins_match=True, fresh_fdt_sha256='2' * 64, dt_overlay_verified=True)
        r.update(deepcopy(self.readback_override))
        return r

    def launch_original_id_stop_once(self, context, bench_sha, intent, allowed_register_commands):
        assert allowed_register_commands == ('STOP',)
        assert bench_sha == self.binding['wide']['bench_sha256']
        assert context['fdt_sha256'] == '2' * 64
        self.actions.append('ID_STOP_ONLY')
        return {'scope': 'SIMULATION_ONLY', 'job_id': 'SIM:ID_STOP'}

    def reconcile_id_stop_readonly(self, intent, job):
        if self.id_stop_pending:
            return {'status': 'PENDING'}
        return {'status': 'SUCCESS', 'context_still_matches': True,
                'identity': [0x56535256, 2, 0x10282601], 'flags': 0, 'lease_left_ms': 0,
                'register_commands': ['STOP', 'STOP'], 'BIND_sent': False, 'REFERENCE_sent': False,
                'ARM_sent': self.bad_stop, 'COMMIT_sent': False, 'transport_close_confirmed': True}

    def wide_context_still_matches(self, evidence):
        return self.wide

    def request_original_camera_start_once(self, intent):
        self.actions.append('RESTORE_ORIGINAL_CAMERA')
        self.camera_job = 'SIM:CAMERA_START'

    def observe_original_camera_restore(self, sealed):
        if not self.restore_complete:
            return {'status': 'PENDING'}
        self.owner = {'pid': 84, 'birth_ticks': 840, 'command_sha256': self.binding['camera_owner']['command_sha256']}
        self.camera_job = None
        self.consumed = True
        seed = deepcopy(sealed['document']['seed'])
        if self.bad_restore_seed:
            seed['primary_period_overruns'] = 0
        return {'status': 'SUCCESS', 'boot_id': self.binding['boot_id'],
                'camera_owner': deepcopy(self.owner), 'dpu_owners': [deepcopy(self.owner)],
                'source_and_model_selection_unchanged': True, 'healthy_source_progress': True,
                'checkpoint_sha256': sealed['pin']['sha256'],
                'exact_seed_before_operator_request': seed, 'consumed_by_this_restore': True,
                'motion_command_emitted': False, 'gui_main_pid': 0, 'saved_listening': False}

    def kill(self, *args):
        raise AssertionError('No path may call kill')

    def clear_lock(self, *args):
        raise AssertionError('No path may clear locks or markers')


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.binding = synthetic_binding()
        self.backend = IsolatedFakeBackend(self.binding)
        self.tx = ReviewTransaction(self.binding, self.backend)
        self.approval = Approval(self.tx.context_sha256,
            frozenset(['NORMAL_CAMERA_STOP', 'SEAL_REAL_CHECKPOINT', 'PL_UNLOAD', 'PL_LOAD_WIDE',
                       'ID_STOP_ONLY', 'RESTORE_ORIGINAL_CAMERA']), 'SIMULATION_APPROVAL_ONLY')

    def stopped(self):
        self.tx.preflight()
        self.tx.request_normal_stop(self.approval)
        self.backend.stop_complete = True
        self.tx.observe_normal_stop()

    def sealed(self):
        self.stopped()
        self.tx.validate_and_seal_checkpoint(self.approval)

    def unloaded(self):
        self.sealed()
        self.tx.request_unload(self.approval)
        self.tx.observe_unload()

    def loaded(self):
        self.unloaded()
        self.tx.request_load_wide(self.approval)
        self.tx.observe_load_wide()

    def stop_verified(self):
        self.loaded()
        self.tx.request_id_stop_only(self.approval)
        self.tx.observe_id_stop_only()

    def test_real_backend_is_impossible(self):
        with self.assertRaises(ExecutionNotReady):
            ReviewTransaction(self.binding, BoardBackendUnavailable())

    def test_no_approval_means_no_stop_or_intent(self):
        self.tx.preflight()
        with self.assertRaises(StageRejected):
            self.tx.request_normal_stop(None)
        self.assertEqual(self.backend.actions, [])
        self.assertEqual(self.tx.snapshot()['intents'], {})

    def test_wrong_context_approval_is_rejected(self):
        self.tx.preflight()
        wrong = Approval('f' * 64, self.approval.actions, 'WRONG_CONTEXT')
        with self.assertRaises(StageRejected):
            self.tx.request_normal_stop(wrong)
        self.assertEqual(self.backend.actions, [])

    def test_cannot_skip_checkpoint_and_unload_stages(self):
        with self.assertRaises(StageRejected):
            self.tx.request_load_wide(self.approval)
        self.assertEqual(self.backend.actions, [])

    def test_stop_pending_preserves_owner_and_never_reissues_stop(self):
        self.tx.preflight()
        self.tx.request_normal_stop(self.approval)
        for _ in range(5):
            self.assertEqual(self.tx.observe_normal_stop()['phase'], 'STOP_PENDING')
        self.assertEqual(self.backend.actions, ['NORMAL_STOP_REQUEST'])
        self.assertEqual(self.backend.owner, self.binding['camera_owner'])
        with self.assertRaises(StageRejected):
            self.tx.request_normal_stop(self.approval)

    def test_intent_is_saved_before_stop_dispatch(self):
        self.tx.preflight()
        original = self.backend.request_normal_camera_stop_once
        def check(intent):
            saved = self.backend.saved_states[-1]
            self.assertEqual(saved['phase'], 'STOP_PENDING')
            self.assertEqual(saved['intents']['NORMAL_CAMERA_STOP'], intent)
            original(intent)
        self.backend.request_normal_camera_stop_once = check
        self.tx.request_normal_stop(self.approval)

    def test_pending_stop_cannot_unload(self):
        self.tx.preflight()
        self.tx.request_normal_stop(self.approval)
        with self.assertRaises(StageRejected):
            self.tx.request_unload(self.approval)
        self.assertNotIn('PL_UNLOAD', self.backend.actions)

    def test_unknown_stop_request_stays_pending_without_retry(self):
        self.tx.preflight()
        def unknown(intent):
            self.backend.actions.append('NORMAL_STOP_REQUEST')
            raise OutcomeUnknown('SIMULATED_STOP_TRANSPORT_LOSS')
        self.backend.request_normal_camera_stop_once = unknown
        self.tx.request_normal_stop(self.approval)
        self.tx.observe_normal_stop()
        self.assertEqual(self.tx.snapshot()['phase'], 'STOP_PENDING')
        self.assertEqual(self.backend.actions, ['NORMAL_STOP_REQUEST'])

    def test_new_unexpected_owner_blocks_unload(self):
        self.sealed()
        self.backend.guard_override = {'dpu_owners': [{'pid': 'SIM:UNEXPECTED'}]}
        with self.assertRaises(HoldRequired):
            self.tx.request_unload(self.approval)
        self.assertNotIn('PL_UNLOAD', self.backend.actions)

    def test_old_boot_checkpoint_is_rejected(self):
        self.stopped()
        doc = deepcopy(self.backend.original_document)
        doc['seed']['boot_id'] = '00000000-0000-4000-8000-000000000099'
        self.backend.raw = self.backend.encode_checkpoint(doc)
        with self.assertRaises(HoldRequired):
            self.tx.validate_and_seal_checkpoint(self.approval)
        self.assertEqual(self.backend.sealed_bytes, [])

    def test_cumulative_overrun_cannot_be_reset(self):
        self.stopped()
        doc = deepcopy(self.backend.original_document)
        doc['seed']['primary_period_overruns'] = 0
        self.backend.raw = self.backend.encode_checkpoint(doc)
        with self.assertRaises(HoldRequired):
            self.tx.validate_and_seal_checkpoint(self.approval)
        self.assertEqual(self.backend.sealed_bytes, [])

    def test_original_validator_refusal_prevents_sealing(self):
        self.stopped()
        self.backend.validator_rejects = True
        with self.assertRaises(HoldRequired):
            self.tx.validate_and_seal_checkpoint(self.approval)
        self.assertEqual(self.backend.validator_calls, 1)
        self.assertEqual(self.backend.sealed_bytes, [])

    def test_exact_bytes_are_sealed_without_json_reencoding(self):
        expected = self.backend.raw
        self.sealed()
        self.assertEqual(self.backend.sealed_bytes, [expected])
        self.assertEqual(self.backend.validator_calls, 1)

    def test_unknown_seal_outcome_holds_without_overwrite(self):
        self.stopped()
        original = self.backend.seal_exact_original_bytes_once
        def unknown(raw, pin, intent):
            original(raw, pin, intent)
            raise OutcomeUnknown('SIMULATED_SEAL_READBACK_LOST')
        self.backend.seal_exact_original_bytes_once = unknown
        with self.assertRaises(HoldRequired):
            self.tx.validate_and_seal_checkpoint(self.approval)
        self.assertEqual(self.tx.snapshot()['phase'], 'HOLD')
        with self.assertRaises(StageRejected):
            self.tx.validate_and_seal_checkpoint(self.approval)
        self.assertEqual(len(self.backend.sealed_bytes), 1)

    def test_loader_pending_never_relaunches(self):
        self.unloaded()
        self.backend.loader_pending['PL_LOAD_WIDE'] = 4
        self.tx.request_load_wide(self.approval)
        for _ in range(4):
            self.assertEqual(self.tx.observe_load_wide()['phase'], 'LOAD_PENDING')
        with self.assertRaises(StageRejected):
            self.tx.request_load_wide(self.approval)
        self.tx.observe_load_wide()
        self.assertEqual(self.backend.actions.count('PL_LOAD_WIDE'), 1)

    def test_unknown_loader_launch_reconciles_without_duplicate(self):
        self.unloaded()
        self.backend.unknown_loader_launch = True
        self.tx.request_load_wide(self.approval)
        self.assertIsNone(self.tx.snapshot()['jobs']['PL_LOAD_WIDE'])
        self.tx.observe_load_wide()
        self.assertEqual(self.backend.actions.count('PL_LOAD_WIDE'), 1)

    def test_wrapper_zero_does_not_hide_real_child_failure(self):
        self.unloaded()
        self.tx.request_load_wide(self.approval)
        self.backend.readback_override = {'wrapper_returncode': 0, 'actual_client_exit_code': 4}
        with self.assertRaises(HoldRequired):
            self.tx.observe_load_wide()
        self.assertEqual(self.tx.snapshot()['phase'], 'HOLD')
        self.assertNotIn('ID_STOP_ONLY', self.backend.actions)

    def test_wrong_vart_holds_even_if_loader_succeeded(self):
        self.unloaded()
        self.tx.request_load_wide(self.approval)
        self.backend.readback_override = {'vart_exact': 'SIMULATED_STALE_BENCHMARK\n'}
        with self.assertRaises(HoldRequired):
            self.tx.observe_load_wide()
        self.assertNotIn('RESTORE_ORIGINAL_CAMERA', self.backend.actions)

    def test_restore_cannot_precede_id_stop(self):
        self.loaded()
        with self.assertRaises(StageRejected):
            self.tx.request_restore_original_camera(self.approval)
        self.assertNotIn('RESTORE_ORIGINAL_CAMERA', self.backend.actions)

    def test_wide_context_change_blocks_first_mmio(self):
        self.loaded()
        self.backend.wide = False
        with self.assertRaises(HoldRequired):
            self.tx.request_id_stop_only(self.approval)
        self.assertNotIn('ID_STOP_ONLY', self.backend.actions)

    def test_pending_stop_job_cannot_hide_foreign_transport_owner(self):
        self.loaded()
        self.tx.request_id_stop_only(self.approval)
        self.backend.id_stop_pending = True
        self.backend.guard_override = {'motion_or_raw_mem_owners': [{'pid': 'SIM:FOREIGN'}]}
        with self.assertRaises(HoldRequired):
            self.tx.observe_id_stop_only()
        self.assertNotIn('RESTORE_ORIGINAL_CAMERA', self.backend.actions)

    def test_illicit_arm_in_stop_receipt_holds(self):
        self.loaded()
        self.tx.request_id_stop_only(self.approval)
        self.backend.bad_stop = True
        with self.assertRaises(HoldRequired):
            self.tx.observe_id_stop_only()
        self.assertNotIn('RESTORE_ORIGINAL_CAMERA', self.backend.actions)

    def test_start_pending_never_restarts_owner(self):
        self.stop_verified()
        self.tx.request_restore_original_camera(self.approval)
        for _ in range(4):
            self.assertEqual(self.tx.observe_restored_camera()['phase'], 'CAMERA_START_PENDING')
        self.assertEqual(self.backend.actions.count('RESTORE_ORIGINAL_CAMERA'), 1)

    def test_restored_seed_must_equal_sealed_seed(self):
        self.stop_verified()
        self.tx.request_restore_original_camera(self.approval)
        self.backend.restore_complete = True
        self.backend.bad_restore_seed = True
        with self.assertRaises(HoldRequired):
            self.tx.observe_restored_camera()
        self.assertEqual(self.tx.snapshot()['phase'], 'HOLD')

    def test_success_remains_platform_only_and_preserves_counter_history(self):
        self.stop_verified()
        self.tx.request_restore_original_camera(self.approval)
        self.backend.restore_complete = True
        result = self.tx.observe_restored_camera()
        self.assertEqual(result['phase'], 'CAMERA_RESTORED_PLATFORM_ONLY_NO_MOTION')
        self.assertEqual(self.backend.actions,
            ['NORMAL_STOP_REQUEST', 'SEAL_REAL_BYTES', 'PL_UNLOAD', 'PL_LOAD_WIDE',
             'ID_STOP_ONLY', 'RESTORE_ORIGINAL_CAMERA'])
        self.assertEqual(result['evidence']['restored_camera']['exact_seed_before_operator_request'],
                         self.backend.original_document['seed'])
        self.assertNotIn('GUI_START', self.backend.actions)


if __name__ == '__main__':
    unittest.main(verbosity=2)
