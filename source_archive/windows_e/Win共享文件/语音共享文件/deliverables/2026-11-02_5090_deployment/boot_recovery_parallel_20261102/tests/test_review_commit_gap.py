"""Minimal after-ledger/before-committed interruption regressions."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('commit_gap_public_fixtures', HERE / 'tests/test_boot_recovery.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


class CommitGapTests(helpers.BindingRollbackTests):
    def test_active_publication_without_committed_receipt_still_has_known_after_bytes(self):
        (self.directory / 'committed.json').unlink()
        result = helpers.install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_before)
        self.assertEqual(self.startup.read_bytes(), self.startup_before)
        self.assertFalse((self.state / 'active-source.json').exists())
        self.assertFalse(result['service_action_requested'])

    def test_tampered_after_snapshot_cannot_authorize_rollback(self):
        (self.directory / 'active-source.after.json').write_bytes(b'unknown after bytes')
        with self.assertRaisesRegex(helpers.rules.Hold, 'AFTER_ACTIVE_LEDGER_SEALED_BYTES_CHANGED'):
            helpers.install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_after)
        self.assertEqual(self.startup.read_bytes(), self.startup_after)


if __name__ == '__main__':
    (HERE / 'test_work').mkdir(exist_ok=True)
    suite = unittest.TestSuite(CommitGapTests(name) for name in (
        'test_active_publication_without_committed_receipt_still_has_known_after_bytes',
        'test_tampered_after_snapshot_cannot_authorize_rollback'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
