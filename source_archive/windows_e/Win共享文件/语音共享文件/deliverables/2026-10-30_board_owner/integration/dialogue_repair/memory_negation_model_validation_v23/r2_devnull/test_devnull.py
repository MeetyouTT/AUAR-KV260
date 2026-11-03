"""Public subprocess regression for the exact null-stream audit exception."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

import worker


class DevnullTests(unittest.TestCase):
    def test_only_exact_null_path_allowed_in_both_phases(self):
        for phase in ('summary', 'metadata_guard'):
            previous = worker.AUDIT_PHASE
            worker.AUDIT_PHASE = phase
            try:
                for path in ('/dev/null', b'/dev/null', Path('/dev/null')):
                    worker.prohibit_private_data_and_devices('open', (path, 'r+', 0))
                for path in ('/dev/NULL', '/dev/null/other', '/dev/./null', '/dev/video0',
                             '/dev/snd/pcmC0D0c', '/dev/zero', '/tmp/private.db',
                             '/tmp/private.sqlite3', '/tmp/private.db-wal'):
                    with self.subTest(phase=phase, path=path), self.assertRaises(RuntimeError):
                        worker.prohibit_private_data_and_devices('open', (path, 'r', 0))
                for event, args in (('sqlite3.connect', (':memory:',)),
                                    ('ctypes.dlopen', ('libvart.so',))):
                    with self.subTest(phase=phase, event=event), self.assertRaises(RuntimeError):
                        worker.prohibit_private_data_and_devices(event, args)
            finally:
                worker.AUDIT_PHASE = previous

    def test_actual_subprocess_devnull_with_installed_audit_hook(self):
        program = r'''
import json, os, subprocess, sys
sys.path.insert(0, sys.argv[1])
import worker
sys.addaudithook(worker.prohibit_private_data_and_devices)
for phase in ('metadata_guard', 'summary'):
    worker.AUDIT_PHASE = phase
    result = subprocess.run(
        [sys.executable, '-B', '-c', 'import sys; assert sys.stdin.read() == ""; print("public-null-ok"); print("discarded", file=sys.stderr)'],
        stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE,
        text=True, timeout=10, check=True)
    assert result.stdout.strip() == 'public-null-ok'
print(json.dumps({'platform': sys.platform, 'actual_null_path': os.devnull, 'phases': 2}))
'''
        result = subprocess.run(
            [sys.executable, '-B', '-c', program, str(Path(__file__).parent)],
            capture_output=True, text=True, timeout=30, check=True)
        self.assertEqual(2, json.loads(result.stdout)['phases'])

    def test_frozen_original_tests_against_r2(self):
        source = Path(__file__).parent.parent / 'test_public_worker.py'
        sys.path.insert(0, str(source.parent))
        try:
            spec = importlib.util.spec_from_file_location('original_public_tests', source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            suite = unittest.defaultTestLoader.loadTestsFromModule(module)
            result = unittest.TestResult()
            suite.run(result)
            self.assertEqual(8, result.testsRun)
            self.assertEqual([], result.errors)
            self.assertEqual([], result.failures)
        finally:
            sys.path.pop(0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
