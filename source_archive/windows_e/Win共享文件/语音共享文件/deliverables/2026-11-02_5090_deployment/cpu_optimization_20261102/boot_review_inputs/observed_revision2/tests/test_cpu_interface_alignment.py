"""Targeted CPU-interface regression cases; no baseline-suite replay or board calls."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))
import recovery_rules as rules

spec = importlib.util.spec_from_file_location('cpu_interface_probe_library', HERE / 'reconcile_cpu_interface.py')
probes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probes)
helpers = probes.module_from('targeted_cpu_interface_case_helpers', HERE / 'tests/test_boot_recovery.py')


class CpuInterfaceMarkerTests(unittest.TestCase):
    def test_real_metadata_marker_path_treats_empty_partial_record_as_consumed(self):
        temporary = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        try:
            recovery = object.__new__(helpers.runtime.Recovery)
            recovery.boot = helpers.BOOT
            recovery.contract = dict(native_boot_policy=dict(new_boot_marker_directory=temporary.name))
            marker = Path(temporary.name) / ('kernel-boot-' + helpers.BOOT + '.consumed')
            self.assertFalse(recovery.current_domain_consumed())
            marker.write_bytes(b'')
            self.assertTrue(recovery.current_domain_consumed())
            self.assertEqual(marker.read_bytes(), b'')
        finally:
            helpers.checked_cleanup(temporary)

    def test_different_boot_preserves_consumed_predecessor_as_archive_only(self):
        value = probes.synthetic_prepare(helpers, old_consumed=True)
        self.assertEqual(value['outcome'], 'ORIGINAL_WIDE_READY_IDSTOP_ONLY')
        self.assertEqual(value['real_commands'], 0)

    def test_current_domain_marker_blocks_before_any_dfx_or_idstop(self):
        value = probes.synthetic_prepare(helpers, domain_consumed=True)
        self.assertEqual(value['outcome'], 'CURRENT_KERNEL_DOMAIN_ALREADY_CONSUMED_OR_UNKNOWN')
        self.assertEqual(value['original_action_names'], [])

    def test_same_boot_consumed_final_still_refused(self):
        with self.assertRaisesRegex(rules.Hold, 'CONSUMED_FINAL_POINTER'):
            rules.verify_final_pointer(helpers.final_fixture(), True,
                                       dict(boot_id=helpers.PREVIOUS, camera_owner=helpers.OWNER),
                                       current_boot=helpers.PREVIOUS, allow_new_kernel_boot=True,
                                       current_domain_consumed=True)

    def test_current_domain_presence_is_unknown_until_observed(self):
        with self.assertRaisesRegex(rules.Hold, 'DOMAIN_ALREADY_CONSUMED_OR_UNKNOWN'):
            rules.verify_final_pointer(helpers.final_fixture(), False,
                                       dict(boot_id=helpers.PREVIOUS, camera_owner=helpers.OWNER),
                                       current_boot=helpers.BOOT, allow_new_kernel_boot=True)

    def test_cold_loader_requires_original_opt_in(self):
        with self.assertRaisesRegex(rules.Hold, 'OPT_IN'):
            rules.verify_final_pointer(helpers.final_fixture(), False,
                                       dict(boot_id=helpers.PREVIOUS, camera_owner=helpers.OWNER),
                                       current_boot=helpers.BOOT, current_domain_consumed=False)

    def test_c6c8_remains_rejected_even_on_archive_route(self):
        with patch.object(rules, 'digest', return_value=rules.FORBIDDEN_OLD_FINAL):
            with self.assertRaisesRegex(rules.Hold, 'C6C8'):
                rules.verify_final_pointer(b'public synthetic source only', True, {},
                                           current_boot=helpers.BOOT, allow_new_kernel_boot=True,
                                           current_domain_consumed=False)


if __name__ == '__main__':
    (HERE / 'test_work').mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CpuInterfaceMarkerTests)
    for name in ('test_camera_gate_records_exact_final_without_consuming_or_rewriting_it',
                 'test_camera_gate_refuses_a_consumed_same_boot_pointer_before_original_start'):
        suite.addTest(helpers.PrepareTests(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
