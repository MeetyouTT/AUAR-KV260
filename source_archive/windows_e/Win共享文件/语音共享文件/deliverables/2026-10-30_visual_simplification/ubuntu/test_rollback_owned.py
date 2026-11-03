"""Verify exact ownership and preservation using temporary files and fake systemd."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import rollback_owned


class RollbackOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aura-rollback-test-')
        self.stage = Path(self.tmp.name)
        self.override = self.stage/'owned.conf'
        self.prior = self.stage/'prior.conf'
        self.prior.write_text('prior override stays')
        self.override.write_text('owned override')
        config = self.stage/'old-config.json'
        launcher = self.stage/'old-launcher.py'
        config.write_text('{}')
        launcher.write_text('# unchanged')
        digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.baseline = dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                             pending_config=str(config),pending_config_sha256=digest(config),
                             pending_launcher=str(launcher),pending_launcher_sha256=digest(launcher),
                             pending={'runtime':'/synthetic/old-runtime'},
                             prior_overrides={str(self.prior):digest(self.prior)},
                             camera_proc={'pid':1234,'start_ticks':'4567'},
                             mechanical_sha256='same',settings={},firmware='same',
                             fdt_sha256='same',vart='same')
        (self.stage/'baseline.json').write_text(json.dumps(self.baseline))
        (self.stage/'transaction.json').write_text(json.dumps(dict(
            override=str(self.override),override_sha256=digest(self.override))))

    def tearDown(self):
        self.tmp.cleanup()

    def test_commit_marker_prevents_rollback(self):
        (self.stage/'commit.json').write_text('{}')
        with patch('rollback_owned.subprocess.run') as run:
            self.assertEqual(rollback_owned.rollback(self.stage)['status'],'SKIPPED_COMMITTED')
            run.assert_not_called()
        self.assertTrue(self.override.exists())

    def test_absent_owned_override_does_not_restart_service(self):
        self.override.unlink()
        with patch('rollback_owned.subprocess.run') as run:
            self.assertEqual(rollback_owned.rollback(self.stage)['status'],'NO_OWN_OVERRIDE')
            run.assert_not_called()

    def test_modified_override_is_never_removed(self):
        self.override.write_text('concurrent edit')
        with patch('rollback_owned.subprocess.run') as run:
            with self.assertRaisesRegex(AssertionError,'modified'):
                rollback_owned.rollback(self.stage)
            run.assert_not_called()
        self.assertEqual(self.override.read_text(),'concurrent edit')

    def test_newer_effective_entry_is_never_overridden(self):
        with patch('rollback_owned.subprocess.check_output',return_value='ExecStart=/newer/config.json'), \
             patch('rollback_owned.subprocess.run') as run:
            with self.assertRaisesRegex(AssertionError,'Concurrent'):
                rollback_owned.rollback(self.stage)
            run.assert_not_called()
        self.assertTrue(self.override.exists())

    def test_only_owned_override_is_removed_and_previous_entry_verified(self):
        after = dict(self.baseline,safe=True,mismatches=[],actual_config=self.baseline['pending_config'],
                     actual_runtime=self.baseline['pending']['runtime'])
        with patch('rollback_owned.subprocess.check_output',return_value=str(self.stage/'startup/config.json')), \
             patch('rollback_owned.subprocess.run') as run, \
             patch('rollback_owned.capture',return_value=after):
            result = rollback_owned.rollback(self.stage)
            self.assertEqual(result['status'],'ROLLED_BACK')
            self.assertEqual(run.call_count,2)
        self.assertFalse(self.override.exists())
        self.assertEqual(self.prior.read_text(),'prior override stays')


if __name__ == '__main__':
    unittest.main(verbosity=2)
