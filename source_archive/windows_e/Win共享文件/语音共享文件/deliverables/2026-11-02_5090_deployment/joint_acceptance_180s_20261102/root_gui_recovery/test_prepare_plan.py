"""Synthetic local metadata only; no production receipt, owner or device access."""
import ast
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import prepare_plan as subject

HERE = Path(__file__).resolve().parent
NOW = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)


def fixture():
    e = json.loads((HERE / 'expected.template.json').read_bytes())
    p = json.loads((HERE / 'phase.template.json').read_bytes())
    boot = '00000000-1111-2222-3333-444444444444'
    e.update(issued_host_utc=NOW.isoformat(), boot_id=boot,
             new_transaction_path_verified_absent=True, prior_unknown_start_or_toggle=False)
    p.update(phase=subject.PHASE, operator='root', permission_active=True,
             cpu_exclusive=False, axis_exclusive=False, other_device_writers_frozen=True,
             issued_host_utc=NOW.isoformat(), expires_host_utc=(NOW + dt.timedelta(minutes=5)).isoformat(),
             boot_id=boot, startup_sha256='a' * 64)
    for name in ('cpu_restore_receipt', 'axis_return_receipt', 'normal_unit_receipt'):
        e[name] = {'path': 'synthetic-' + name + '.json', 'sha256': 'b' * 64}
        p[name + '_sha256'] = 'b' * 64
    e['startup'].update(sha256='a' * 64, component_map_sha256='c' * 64, all_components_verified=True,
                        four_core_sha256={k: 'd' * 64 for k in subject.CORE})
    own = {'pid': 100, 'birth_ticks': '100', 'command_sha256': 'e' * 64}
    e['camera'].update(boot_id=boot, owner=own, run_config_path='/synthetic/current/config.json',
                       run_config_sha256='f' * 64, source_advancing_verified=True,
                       protected_restore_audit_passed=True)
    e['face_readback'].update(selected_path='/synthetic/selected.json', selected_sha256='0' * 64,
                              gui_config_sha256='1' * 64, verifier_source_sha256='2' * 64,
                              pure_original_verify_passed=True, complete_source_closure_verified=True,
                              current_run_config_in_pins=True, no_store_clock_or_writer_constructed=True,
                              verified_camera_owner=copy.deepcopy(own))
    e['gui'].update(main_pid=0, active_state='inactive', sub_state='dead', job='',
                    saved_listening_enabled=False, microphone_open=False,
                    normal_service_restore_plan_verified=True)
    for k, v in tuple(e['inference'].items()):
        if type(v) is bool:
            e['inference'][k] = True
    return e, p


class ContractTests(unittest.TestCase):
    def check_fixture(self, edit=None, code=None):
        e, p = fixture()
        if edit:
            edit(e, p)
        loader = lambda path, sha: {'synthetic': True}
        if code:
            with self.assertRaisesRegex(ValueError, '^' + code + '$'):
                subject.validate(e, p, NOW, loader)
        else:
            result = subject.validate(e, p, NOW, loader)
            self.assertIs(result['may_execute'], False)
            self.assertIs(result['original_start_submitted'], False)

    def test_valid_is_still_plan_only(self): self.check_fixture()
    def test_old_phase_blocks(self):
        self.check_fixture(lambda e, p: p.update(phase='PREPARING_ORIGINAL_WIDE_PROTECTED_RECOVERY'), 'ROOT_GUI_PHASE_NOT_GRANTED')
    def test_not_root_blocks(self):
        self.check_fixture(lambda e, p: p.update(operator='cpu'), 'ROOT_GUI_PHASE_NOT_GRANTED')
    def test_cpu_still_owns_blocks(self):
        self.check_fixture(lambda e, p: p.update(cpu_exclusive=True), 'EXCLUSIVE_HANDOFF_REQUIRED')
    def test_axis_still_owns_blocks(self):
        self.check_fixture(lambda e, p: p.update(axis_exclusive=True), 'EXCLUSIVE_HANDOFF_REQUIRED')
    def test_stale_expected_blocks(self):
        self.check_fixture(lambda e, p: e.update(issued_host_utc=(NOW - dt.timedelta(seconds=601)).isoformat()), 'FRESH_HOST_RECEIPT_REQUIRED')
    def test_expired_phase_blocks(self):
        self.check_fixture(lambda e, p: p.update(expires_host_utc=NOW.isoformat()), 'ROOT_GUI_PHASE_EXPIRED_OR_UNBOUNDED')
    def test_phase_wrong_boot_blocks(self):
        self.check_fixture(lambda e, p: p.update(boot_id='different'), 'PHASE_BOOT_MISMATCH')
    def test_phase_wrong_receipt_blocks(self):
        self.check_fixture(lambda e, p: p.update(cpu_restore_receipt_sha256='9' * 64), 'PHASE_RECEIPT_MISMATCH')
    def test_missing_380_blocks(self):
        self.check_fixture(lambda e, p: e['startup'].update(component_count=379), 'ALL_380_REQUIRED')
    def test_missing_core_blocks(self):
        self.check_fixture(lambda e, p: e['startup']['four_core_sha256'].pop(next(iter(subject.CORE))), 'FRESH_FOUR_CORE_REQUIRED')
    def test_camera_bool_pid_blocks(self):
        self.check_fixture(lambda e, p: e['camera']['owner'].update(pid=True), 'CAMERA_PID_REQUIRED')
    def test_unproven_progress_blocks(self):
        self.check_fixture(lambda e, p: e['camera'].update(source_advancing_verified=False), 'CAMERA_RESTORE_PROOF_REQUIRED')
    def test_27pins_needs_review_not_silent_rewrite(self):
        self.check_fixture(lambda e, p: e['face_readback'].update(source_pin_count=27), 'REVIEW_26_PIN_CONTRACT_MISMATCH')
    def test_wrong_binding_owner_blocks(self):
        self.check_fixture(lambda e, p: e['face_readback']['verified_camera_owner'].update(pid=101), 'BINDING_OWNER_MISMATCH')
    def test_fake_verify_blocks(self):
        self.check_fixture(lambda e, p: e['face_readback'].update(no_store_clock_or_writer_constructed=False), 'PURE_BINDING_VERIFY_REQUIRED')
    def test_running_gui_blocks(self):
        self.check_fixture(lambda e, p: e['gui'].update(main_pid=2), 'GUI_NORMAL_STOP_REQUIRED')
    def test_unknown_intent_blocks(self):
        self.check_fixture(lambda e, p: e.update(prior_unknown_start_or_toggle=True), 'UNKNOWN_OR_EXISTING_INTENT_BLOCKS_RETRY')
    def test_existing_transaction_blocks(self):
        self.check_fixture(lambda e, p: e.update(new_transaction_path_verified_absent=False), 'UNKNOWN_OR_EXISTING_INTENT_BLOCKS_RETRY')
    def test_changed_model_blocks(self):
        self.check_fixture(lambda e, p: e['inference'].update(model='other'), 'ORIGINAL_INFERENCE_PARAMETERS_REQUIRED')
    def test_missing_date_blocks(self):
        self.check_fixture(lambda e, p: e['inference'].update(date_header_verified=False), 'ORIGINAL_CLOCK_AND_VOICE_PROOF_REQUIRED')


class LocalOnlyTests(unittest.TestCase):
    def test_hashed_file_and_changed_file(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / 'receipt.json'; p.write_bytes(b'{"synthetic":true}\n')
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertTrue(subject.local_hashed_json(p, sha, Path(work))['synthetic'])
            p.write_bytes(b'{"synthetic":false}\n')
            with self.assertRaisesRegex(ValueError, '^FILE_SHA_MISMATCH$'):
                subject.local_hashed_json(p, sha, Path(work))

    def test_path_outside_joint_blocks(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / 'receipt.json'; p.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, '^RECEIPT_OUTSIDE_JOINT$'):
                subject.local_hashed_json(p, hashlib.sha256(b'{}').hexdigest(), Path(work) / 'other')

    def test_template_cannot_pass(self):
        e = json.loads((HERE / 'expected.template.json').read_bytes())
        p = json.loads((HERE / 'phase.template.json').read_bytes())
        with self.assertRaisesRegex(ValueError, '^ROOT_GUI_PHASE_NOT_GRANTED$'):
            subject.validate(e, p, NOW, lambda *a: {})

    def test_no_device_execution_capabilities(self):
        tree = ast.parse((HERE / 'prepare_plan.py').read_bytes())
        imports = {n.names[0].name for n in tree.body if isinstance(n, ast.Import)}
        self.assertEqual(imports, {'argparse', 'datetime', 'hashlib', 'json', 're'})
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                             and n.func.id in {'exec', 'eval', 'compile', '__import__'} for n in ast.walk(tree)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
