import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).with_name('bench_identity_stop.py')


class BenchPlanTests(unittest.TestCase):
    def test_default_only_prints_plan(self):
        value = subprocess.run([sys.executable, '-B', str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(value.returncode, 0)
        plan = json.loads(value.stdout)
        self.assertFalse(plan['board_accessed'])
        self.assertFalse(plan['ARM'])
        self.assertFalse(plan['COMMIT'])
        self.assertEqual(plan['register_commands'], ['STOP'])

    def test_missing_confirmation_refused_before_files(self):
        value = subprocess.run([sys.executable, '-B', str(SCRIPT), '--execute'], capture_output=True, text=True)
        self.assertNotEqual(value.returncode, 0)
        self.assertIn('Explicit ID_STOP_ONLY confirmation required; no MMIO', value.stderr)

    @unittest.skipIf(platform.machine() == 'aarch64', 'This rejection specifically checks the x86 host')
    def test_confirmed_host_still_refused(self):
        value = subprocess.run([sys.executable, '-B', str(SCRIPT), '--execute', '--confirmation', 'ID_STOP_ONLY'], capture_output=True, text=True)
        self.assertNotEqual(value.returncode, 0)
        self.assertIn('host execution refused', value.stderr)


if __name__ == '__main__':
    unittest.main()
