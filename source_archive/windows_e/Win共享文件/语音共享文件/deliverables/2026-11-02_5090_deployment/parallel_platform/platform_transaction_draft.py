"""Local review/simulation of a strictly staged platform transaction.

EXECUTION_NOT_READY: this module has no SSH, shell, device or board-file backend.
Importing or running it cannot operate the KV260. A future real backend and its
durable intent/reconciliation behavior require separate review before release.
There is deliberately no run-all, execute-board or force/retry action.
"""
from dataclasses import dataclass
from copy import deepcopy
import hashlib
import json


RELEASE_STATUS = 'EXECUTION_NOT_READY'
RELEASE_GAPS = (
    'Real board backend and durable board-side intent ledger are not implemented.',
    'Loader backend must capture the actual dfx-mgr-client child result and reconcile pending jobs without retransmission.',
    'Original validator must execute in a verified module namespace; its safe branch was statically reviewed, never executed here.',
    'Current user facts authorize observation only; no PL-switch or new-motion approval has been recorded.',
)


class ExecutionNotReady(RuntimeError):
    pass


class StageRejected(RuntimeError):
    pass


class HoldRequired(RuntimeError):
    pass


class OutcomeUnknown(RuntimeError):
    """The request may have reached its owner. Inspect, never retransmit."""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise HoldRequired(message)


@dataclass(frozen=True)
class Approval:
    context_sha256: str
    actions: frozenset
    receipt_reference: str
    simulation_only: bool = True


class BoardBackendUnavailable:
    """Hard stop: intentionally contains no transport or subprocess code."""
    simulation_only = False

    def __getattr__(self, _):
        raise ExecutionNotReady('; '.join(RELEASE_GAPS))


class ReviewTransaction:
    """One explicit method per stage; only an isolated simulator is accepted.

    This is the reviewable transaction model, not the production executor.
    A call never automatically advances into the next mutation stage.
    State snapshots can be inspected after each method. All unknown mutation
    outcomes stay pending; a completed failure enters HOLD without rollback.
    """
    def __init__(self, binding, backend):
        if getattr(backend, 'simulation_only', False) is not True:
            raise ExecutionNotReady('; '.join(RELEASE_GAPS))
        self.binding = deepcopy(binding)
        self.backend = backend
        self.context_sha256 = sha(json.dumps(binding, sort_keys=True, separators=(',', ':')).encode())
        self.session = {'schema': 'aura-platform-transaction-simulation-1',
                        'scope': 'SIMULATION_ONLY_NO_BOARD_EVIDENCE',
                        'phase': 'NEW', 'binding': deepcopy(binding),
                        'context_sha256': self.context_sha256, 'evidence': {},
                        'intents': {}, 'jobs': {}, 'hold': None}

    def snapshot(self):
        return deepcopy(self.session)

    def _stage(self, *allowed):
        if self.session['phase'] not in allowed:
            raise StageRejected('Expected ' + '/'.join(allowed) + '; actual ' + self.session['phase'])

    def _approval(self, approval, action):
        if not (isinstance(approval, Approval) and approval.simulation_only is True and
                approval.context_sha256 == self.context_sha256 and
                action in approval.actions and approval.receipt_reference):
            raise StageRejected('No explicit context-bound approval for ' + action)

    def _hold(self, message):
        self.session['hold'] = message
        self.session['phase'] = 'HOLD'
        self.backend.persist_simulation_state(self.snapshot())
        raise HoldRequired(message)

    def _guard(self, owner_mode):
        try:
            observed = self.backend.recheck(self.binding, self.snapshot())
            require(observed['boot_id'] == self.binding['boot_id'], 'Boot changed')
            require(observed['startup_sha256'] == self.binding['startup_sha256'], 'Startup changed')
            require(observed['gui_main_pid'] == 0 and observed['gui_job'] is None, 'GUI writer appeared')
            require(observed['saved_listening'] is False, 'Listening is not paused')
            require(observed['inspection_complete'] is True, 'Incomplete owner inventory')
            if owner_mode == 'id_stop_job' and observed['motion_or_raw_mem_owners']:
                require(len(observed['motion_or_raw_mem_owners']) == 1 and
                        observed.get('id_stop_job_identity_verified') is True and
                        observed.get('id_stop_job_intent') == self.session['intents']['ID_STOP_ONLY'],
                        'Motion transport does not belong to the exact saved ID/STOP job')
            else:
                require(observed['motion_or_raw_mem_owners'] == [], 'Motion or raw-memory owner appeared')
            if self.session['phase'] in ('WIDE_VERIFIED', 'ID_STOP_PENDING', 'ID_STOP_VERIFIED', 'CAMERA_START_PENDING'):
                require(self.backend.wide_context_still_matches(self.session['evidence']['wide']) is True,
                        'Loaded wide context changed')
            if owner_mode == 'original':
                require(observed['camera_owner'] == self.binding['camera_owner'], 'Original owner identity changed')
                require(observed['dpu_owners'] == [self.binding['camera_owner']], 'Unexpected DPU owner')
                require(observed['camera_shutdown_protection'] is True, 'Normal-shutdown protections changed')
            elif owner_mode in ('none', 'id_stop_job'):
                require(observed['camera_owner'] is None and observed['camera_job'] is None, 'Camera owner/job remains')
                require(observed['dpu_owners'] == [], 'DPU owner remains')
            elif owner_mode == 'stopping':
                require(observed['camera_owner'] in (None, self.binding['camera_owner']), 'Replacement owner during shutdown')
                require(all(owner == self.binding['camera_owner'] for owner in observed['dpu_owners']), 'Unexpected DPU owner')
            elif owner_mode == 'starting':
                current = observed['camera_owner']
                if current is not None:
                    old = self.binding['camera_owner']
                    require(current.get('command_sha256') == old['command_sha256'] and
                            (current.get('pid'), current.get('birth_ticks')) != (old['pid'], old['birth_ticks']),
                            'Started owner is not the original camera command in a new process')
                require(observed['dpu_owners'] in ([], [current]) if current is not None else observed['dpu_owners'] == [],
                        'Unexpected DPU owner during startup')
            return observed
        except HoldRequired as error:
            self._hold(str(error))

    def _intent(self, action, approval):
        self._approval(approval, action)
        require(action not in self.session['intents'], 'Intent already exists; do not retransmit')
        intent = {'action': action, 'ordinal': len(self.session['intents']) + 1,
                  'context_sha256': self.context_sha256,
                  'approval_reference': approval.receipt_reference,
                  'scope': 'SIMULATION_ONLY_NO_BOARD_EVIDENCE'}
        self.session['intents'][action] = intent
        self.backend.persist_simulation_state(self.snapshot())
        return deepcopy(intent)

    def preflight(self):
        self._stage('NEW')
        self._guard('original')
        proof = self.backend.read_preflight(self.binding)
        if not proof['all_source_and_firmware_pins_match']:
            self._hold('Source or firmware closure changed')
        self.session['evidence']['preflight'] = deepcopy(proof)
        self.session['phase'] = 'PREFLIGHTED'
        return self.snapshot()

    def request_normal_stop(self, approval):
        self._stage('PREFLIGHTED')
        self._approval(approval, 'NORMAL_CAMERA_STOP')
        self._guard('original')
        intent = self._intent('NORMAL_CAMERA_STOP', approval)
        self.session['phase'] = 'STOP_PENDING'
        self.backend.persist_simulation_state(self.snapshot())
        try:
            self.backend.request_normal_camera_stop_once(intent)
        except OutcomeUnknown as error:
            self.session['evidence']['stop_request_unknown'] = str(error)
        return self.snapshot()

    def observe_normal_stop(self):
        self._stage('STOP_PENDING')
        self._guard('stopping')
        observed = self.backend.observe_camera_stop(self.session['intents']['NORMAL_CAMERA_STOP'])
        if observed['status'] == 'PENDING':
            return self.snapshot()
        if not (observed['status'] == 'SUCCESS' and observed['original_owner_gone'] is True and
                observed['unit_main_pid'] == 0 and observed['unit_job'] is None and
                observed['unit_result'] == 'success' and observed['exec_main_status'] == 0):
            self._hold('Camera did not complete a confirmed normal shutdown')
        self._guard('none')
        self.session['evidence']['normal_stop'] = deepcopy(observed)
        self.session['phase'] = 'CAMERA_STOPPED'
        return self.snapshot()

    def validate_and_seal_checkpoint(self, approval):
        self._stage('CAMERA_STOPPED')
        self._approval(approval, 'SEAL_REAL_CHECKPOINT')
        self._guard('none')
        try:
            result = self.backend.read_actual_checkpoint()
            raw, path = result['exact_bytes'], result['path']
            require(type(raw) is bytes, 'Exact original checkpoint bytes required')
            digest = sha(raw)
            require(digest != self.binding['previous_checkpoint_sha256'], 'Historical checkpoint has not refreshed')
            document = json.loads(raw)
            s, a = document['seed'], document['auxiliary']
            owner = self.binding['camera_owner']
            require(document['schema'] == 'aura-native-protection-checkpoint-2', 'Wrong checkpoint schema')
            require(document['scope'] == 'final_quiescent_before_native_owner_close', 'Not a final checkpoint')
            require(s['purpose'] == 'final_quiescent_business_checkpoint' and s['checkpoint_kind'] == 1, 'Wrong seed scope')
            require(s['boot_id'] == self.binding['boot_id'] and s['source_pid'] == owner['pid'] and
                    s['source_birth_ticks'] == owner['birth_ticks'], 'Checkpoint predecessor identity differs')
            require(document['source_unit_sha256'] == self.binding['source_unit_sha256'], 'Source unit changed')
            require(s['source_manifest_sha256'] == self.binding['source_manifest_sha256'], 'Source manifest changed')
            require(result['captured_after_stop_intent'] is True and result['capture_in_current_monotonic_domain'] is True,
                    'Checkpoint time does not follow this stop intent')
            require(a['active'] == a['primary_waiting'] == a['fenced'] == s['fenced'] == 0 and
                    a['pending_result_tokens'] == [0, 0, 0], 'Checkpoint is busy, fenced or incomplete')
            floors = self.binding['counter_lower_bounds']
            require(s['primary_calls'] >= floors['primary_calls'] and
                    s['primary_period_overruns'] >= floors['primary_period_overruns'] and
                    a['sface_counters']['completed'] >= floors['sface_completed'], 'Cumulative history decreased')
            require(result['previous_kernel_archive_chain_verified'] is True, 'Previous-kernel history not verified')
            pin = {'path': path, 'sha256': digest}
            # The future backend must call the ORIGINAL function against this
            # exact file, in its verified namespace, without consume_checkpoint.
            validated = self.backend.call_original_load_business_checkpoint(pin, self.binding['boot_id'])
            require(validated['sha256'] == digest and validated['document'] == document and
                    validated['seed'] == s and validated['auxiliary'] == a, 'Original validator returned different state')
            require(self.backend.checkpoint_still_exact_and_unconsumed(pin) is True, 'Checkpoint changed or was consumed')
            intent = self._intent('SEAL_REAL_CHECKPOINT', approval)
            self.session['phase'] = 'CHECKPOINT_SEAL_PENDING'
            self.backend.persist_simulation_state(self.snapshot())
            sealed = self.backend.seal_exact_original_bytes_once(raw, pin, intent)
            require(sealed['created_exclusively'] is True and sealed['readback_sha256'] == digest,
                    'Exact-byte sealing was not confirmed')
            self.session['evidence']['sealed_checkpoint'] = {
                'pin': pin, 'sealed_path': sealed['path'], 'document': deepcopy(document),
                'exact_bytes_sha256': digest, 'original_validator_passed': True}
            self.session['phase'] = 'CHECKPOINT_SEALED'
            return self.snapshot()
        except (HoldRequired, OutcomeUnknown, ValueError, KeyError, TypeError) as error:
            self._hold('Checkpoint stage: ' + str(error))

    def _sealed_guard(self):
        proof = self.session['evidence']['sealed_checkpoint']
        if self.backend.checkpoint_still_exact_and_unconsumed(proof['pin']) is not True:
            self._hold('Sealed checkpoint no longer available for one-time restore')

    def _launch_once(self, action, approval, phase):
        self._approval(approval, action)
        self._guard('none')
        self._sealed_guard()
        intent = self._intent(action, approval)
        self.session['phase'] = phase
        self.backend.persist_simulation_state(self.snapshot())
        try:
            job = self.backend.launch_loader_once(action, intent)
            self.session['jobs'][action] = deepcopy(job)
        except OutcomeUnknown as error:
            # No handle does NOT prove no child. Only reconcile/poll is allowed.
            self.session['jobs'][action] = None
            self.session['evidence'][action + '_unknown'] = str(error)
        return self.snapshot()

    def request_unload(self, approval):
        self._stage('CHECKPOINT_SEALED')
        return self._launch_once('PL_UNLOAD', approval, 'UNLOAD_PENDING')

    def observe_unload(self):
        self._stage('UNLOAD_PENDING')
        self._guard('none')
        r = self.backend.reconcile_loader_readonly('PL_UNLOAD', self.session['intents']['PL_UNLOAD'],
                                                  self.session['jobs']['PL_UNLOAD'])
        if r['status'] == 'PENDING':
            return self.snapshot()
        if not (r['status'] == 'SUCCESS' and r['actual_client_identity_verified'] is True and
                r['actual_client_exit_code'] == 0 and r['fresh_readback_verified'] is True and
                r['active_application'] is None):
            self._hold('Unload was not confirmed by actual client and fresh platform readback')
        self.session['evidence']['unload'] = deepcopy(r)
        self.session['phase'] = 'UNLOADED'
        return self.snapshot()

    def request_load_wide(self, approval):
        self._stage('UNLOADED')
        return self._launch_once('PL_LOAD_WIDE', approval, 'LOAD_PENDING')

    def observe_load_wide(self):
        self._stage('LOAD_PENDING')
        self._guard('none')
        r = self.backend.reconcile_loader_readonly('PL_LOAD_WIDE', self.session['intents']['PL_LOAD_WIDE'],
                                                  self.session['jobs']['PL_LOAD_WIDE'])
        if r['status'] == 'PENDING':
            return self.snapshot()
        expected = self.binding['wide']
        if not (r['status'] == 'SUCCESS' and r['actual_client_identity_verified'] is True and
                r['actual_client_exit_code'] == 0 and r['fresh_readback_verified'] is True and
                r['boot_id'] == self.binding['boot_id'] and r['active_application'] == expected['app'] and
                r['firmware_name'] == expected['firmware_name'] and r['fpga_state'] == 'operating' and
                r['vart_exact'] == expected['vart_exact'] and r['all_runtime_and_driver_pins_match'] is True and
                r['fresh_fdt_sha256'] and r['dt_overlay_verified'] is True):
            self._hold('Wide platform readback/pairing/client result not confirmed')
        # Fresh FDT is obtained from this load. It is never supplied as an old
        # expected hash, and it does not grant a physical position reference.
        self.session['evidence']['wide'] = deepcopy(r)
        self.session['phase'] = 'WIDE_VERIFIED'
        return self.snapshot()

    def request_id_stop_only(self, approval):
        self._stage('WIDE_VERIFIED')
        self._approval(approval, 'ID_STOP_ONLY')
        self._guard('none')
        context = {'boot_id': self.binding['boot_id'],
                   'fdt_sha256': self.session['evidence']['wide']['fresh_fdt_sha256'],
                   'firmware_name': self.binding['wide']['firmware_name']}
        intent = self._intent('ID_STOP_ONLY', approval)
        self.session['phase'] = 'ID_STOP_PENDING'
        self.backend.persist_simulation_state(self.snapshot())
        try:
            self.session['jobs']['ID_STOP_ONLY'] = self.backend.launch_original_id_stop_once(
                context, self.binding['wide']['bench_sha256'], intent,
                allowed_register_commands=('STOP',))
        except OutcomeUnknown as error:
            self.session['jobs']['ID_STOP_ONLY'] = None
            self.session['evidence']['ID_STOP_ONLY_unknown'] = str(error)
        return self.snapshot()

    def observe_id_stop_only(self):
        self._stage('ID_STOP_PENDING')
        # During a pending STOP-only process its own mapped transport is valid.
        # The backend must tie that sole exception to the exact saved job identity.
        self._guard('id_stop_job')
        r = self.backend.reconcile_id_stop_readonly(self.session['intents']['ID_STOP_ONLY'],
                                                   self.session['jobs']['ID_STOP_ONLY'])
        if r['status'] == 'PENDING':
            return self.snapshot()
        if not (r['status'] == 'SUCCESS' and r['context_still_matches'] is True and
                r['identity'] == [0x56535256, 2, 0x10282601] and r['flags'] == 0 and r['lease_left_ms'] == 0 and
                r['register_commands'] and set(r['register_commands']) == {'STOP'} and
                r['BIND_sent'] is False and r['REFERENCE_sent'] is False and
                r['ARM_sent'] is False and r['COMMIT_sent'] is False and r['transport_close_confirmed'] is True):
            self._hold('ID/STOP-only identity, commands or disabled output not confirmed')
        self._guard('none')
        self.session['evidence']['id_stop'] = deepcopy(r)
        self.session['phase'] = 'ID_STOP_VERIFIED'
        return self.snapshot()

    def request_restore_original_camera(self, approval):
        self._stage('ID_STOP_VERIFIED')
        self._approval(approval, 'RESTORE_ORIGINAL_CAMERA')
        self._guard('none')
        self._sealed_guard()
        if self.backend.wide_context_still_matches(self.session['evidence']['wide']) is not True:
            self._hold('Wide context changed before restore')
        intent = self._intent('RESTORE_ORIGINAL_CAMERA', approval)
        self.session['phase'] = 'CAMERA_START_PENDING'
        self.backend.persist_simulation_state(self.snapshot())
        try:
            self.backend.request_original_camera_start_once(intent)
        except OutcomeUnknown as error:
            self.session['evidence']['camera_start_unknown'] = str(error)
        return self.snapshot()

    def observe_restored_camera(self):
        self._stage('CAMERA_START_PENDING')
        # A new camera owner is expected here; the backend binds it to its real
        # systemd PID/birth and the original command, not a guessed replacement.
        self._guard('starting')
        r = self.backend.observe_original_camera_restore(self.session['evidence']['sealed_checkpoint'])
        if r['status'] == 'PENDING':
            return self.snapshot()
        sealed = self.session['evidence']['sealed_checkpoint']
        old = self.binding['camera_owner']
        new = r.get('camera_owner', {})
        if not (r['status'] == 'SUCCESS' and r['boot_id'] == self.binding['boot_id'] and
                (new.get('pid'), new.get('birth_ticks')) != (old['pid'], old['birth_ticks']) and
                new.get('command_sha256') == old['command_sha256'] and r['dpu_owners'] == [new] and
                r['source_and_model_selection_unchanged'] is True and r['healthy_source_progress'] is True and
                r['checkpoint_sha256'] == sealed['pin']['sha256'] and
                r['exact_seed_before_operator_request'] == sealed['document']['seed'] and
                r['consumed_by_this_restore'] is True and r['motion_command_emitted'] is False and
                r['gui_main_pid'] == 0 and r['saved_listening'] is False):
            self._hold('Original camera/checkpoint ownership restoration not confirmed')
        self.session['evidence']['restored_camera'] = deepcopy(r)
        self.session['phase'] = 'CAMERA_RESTORED_PLATFORM_ONLY_NO_MOTION'
        return self.snapshot()


def main():
    print(json.dumps({'release_status': RELEASE_STATUS, 'release_gaps': RELEASE_GAPS,
        'board_operations_implemented': False, 'board_mutations': False,
        'simulation_module': 'test_platform_transaction_draft.py',
        'stages': ['preflight', 'request_normal_stop', 'observe_normal_stop',
                   'validate_and_seal_checkpoint', 'request_unload', 'observe_unload',
                   'request_load_wide', 'observe_load_wide', 'request_id_stop_only',
                   'observe_id_stop_only', 'request_restore_original_camera', 'observe_restored_camera']}, indent=2))


if __name__ == '__main__':
    main()
