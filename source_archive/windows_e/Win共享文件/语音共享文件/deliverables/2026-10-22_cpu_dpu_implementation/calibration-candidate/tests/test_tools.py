import bootstrap
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('calibration_operator_tested', ROOT/'tools/calibration_operator.py')
operator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(operator)


class ToolTests(unittest.TestCase):
    def test_standard_library_check_blocks_runtime_and_does_not_create_files(self):
        source = ROOT/'candidate/aura/board/identity/sface_calibration.py'
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(['python', '-B', str(ROOT/'tools/calibration_contract_check.py'),
                '--module', str(source), '--expected-sha256', digest], cwd=folder,
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])
        output = json.loads(result.stdout)
        self.assertEqual(output['checks_passed'], 8)
        self.assertFalse(output['runtime_verified'])
        self.assertFalse(output['database_created'])
        wrong = subprocess.run(['python', '-B', str(ROOT/'tools/calibration_contract_check.py'),
                '--module', str(source), '--expected-sha256', '0'*64], capture_output=True, text=True)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertNotIn('session_token', wrong.stderr)

    def test_operator_reads_private_token_uses_only_loopback_and_no_proxy_or_redirect(self):
        captured = []
        response = io.BytesIO(b'{"mode":"CALIBRATION_ONLY","sessions":0}')
        def opener(*handlers):
            self.assertTrue(any(type(h).__name__ == 'ProxyHandler' and h.proxies == {} for h in handlers))
            self.assertTrue(any(h is operator.NoRedirect or isinstance(h, operator.NoRedirect) for h in handlers))
            def open_request(request, timeout):
                captured.append(request)
                self.assertEqual(timeout, 3)
                return response
            return SimpleNamespace(open=open_request)
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/'synthetic-private-config.json'
            config.write_text(json.dumps({'dpu_sface_calibration': {'enabled': True,
                       'mode': 'CALIBRATION_ONLY', 'control_token': 'c'*64}}))
            output = io.StringIO()
            params = json.dumps({'purpose': 'calibration_gallery', 'person': 'P_A',
                                 'capture_session': 'C_ONE', 'target': {'camera_epoch': 'test',
                                 'track_id': 1, 'track_generation': 1}})
            with patch.object(operator, 'build_opener', opener), patch('sys.stdin', io.StringIO(params)), contextlib.redirect_stdout(output):
                self.assertEqual(operator.main(['--private-config', str(config), '--port', '8766', '--action', 'start']), 0)
        self.assertEqual(captured[0].full_url, 'http://127.0.0.1:8766/v1/ui/sface-calibration')
        self.assertEqual(captured[0].get_header('Authorization'), 'Bearer '+'c'*64)
        self.assertIn('request_id', json.loads(captured[0].data)['params'])
        self.assertNotIn('c'*64, output.getvalue())
        with self.assertRaises(ValueError): operator.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://example.test')

    def test_operator_rejects_unconfigured_candidate_without_echoing_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder)/'synthetic-private-config.json'
            config.write_text(json.dumps({'dpu_sface_calibration': {'enabled': False,
                         'control_token': 'private-synthetic-placeholder'}}))
            output = io.StringIO()
            with patch.object(operator, 'build_opener', side_effect=AssertionError('Must not connect')), contextlib.redirect_stderr(output):
                self.assertEqual(operator.main(['--private-config', str(config), '--port', '8766', '--action', 'health']), 1)
        self.assertNotIn('private-synthetic-placeholder', output.getvalue())


if __name__ == '__main__': unittest.main()
