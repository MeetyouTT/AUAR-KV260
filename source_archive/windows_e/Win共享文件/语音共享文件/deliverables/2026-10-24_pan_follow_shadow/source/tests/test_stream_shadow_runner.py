"""Exercise the real stream consumer against a fixture HTTP camera service."""
import contextlib
import http.client
from http.server import ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = Path('/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
sys.path.insert(0, str(ROOT/'stream_v2'))
sys.path.insert(0, str(APP))
from board.vision import ui_camera_service as camera
from board.motion.camera_feed import install as install_feed
from motion_stream import install
install_feed(camera)
install(camera)
spec = importlib.util.spec_from_file_location('stream_runner', ROOT/'stream_v2/run_shadow_stream.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def run_fixture(self, keep_publishing):
        state = camera.CameraState(Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        stop = threading.Event()
        def publish():
            fid = 0
            while not stop.is_set():
                fid += 1
                stamp = int(time.monotonic()*1000)
                state.captured(stamp)
                state.observed(fid, stamp, {'target_id': 1, 'tracks': [
                    {'track_id': 1, 'generation': 1, 'visible': True, 'confirmed': True,
                     'frame_id': fid, 'captured_at': stamp/1000., 'box': [200., 0., 80., 480.], 'score': .9}]}, 1.)
                if not keep_publishing:
                    return
                stop.wait(.04)
        publisher = threading.Thread(target=publish)
        publisher.start()
        server = ThreadingHTTPServer(('127.0.0.1', 0), camera.handler_for(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        original_connection = http.client.HTTPConnection
        try:
            with tempfile.TemporaryDirectory() as folder:
                out = Path(folder)/'result.jsonl'
                argv = ['run_shadow_stream.py', '--app-root', str(APP), '--config', str(ROOT/'stream_v2/config.json'),
                        '--output', str(out), '--duration', '.6']
                with patch.object(sys, 'argv', argv), patch.object(runner.os, 'uname', return_value=SimpleNamespace(machine='aarch64')):
                    with patch.object(runner.http.client, 'HTTPConnection', side_effect=lambda *a, **kw: original_connection('127.0.0.1', server.server_port, timeout=kw.get('timeout', 1))):
                        with contextlib.redirect_stdout(io.StringIO()):
                            code = runner.main()
                result = json.loads(Path(str(out)+'.summary.json').read_text())
                self.assertEqual(out.stat().st_mode & 0o777, 0o600)
                self.assertNotIn('target', json.loads(out.read_text().splitlines()[0]))
                return code, result
        finally:
            stop.set()
            publisher.join(1)
            server.shutdown()
            server.server_close()

    def test_complete_window_preserves_source_and_has_no_physical_output(self):
        code, r = self.run_fixture(True)
        self.assertEqual(code, 0)
        self.assertEqual(r['final_reason'], 'TIME_LIMIT')
        self.assertTrue(r['full_duration_completed'])
        self.assertGreaterEqual(r['distinct_ready_sources'], 5)
        self.assertGreater(r['suggestion_count'], 0)
        self.assertFalse(r['physical_actuation'])
        self.assertEqual(r['register_writes'], 0)
        self.assertEqual(r['suggestion_limits_us'], [1425, 1445])

    def test_frozen_source_latches_and_does_not_complete_window(self):
        code, r = self.run_fixture(False)
        self.assertEqual(code, 0)
        self.assertEqual(r['final_reason'], 'SOURCE_EXPIRED')
        self.assertFalse(r['full_duration_completed'])
        self.assertEqual(r['suggestion_count'], 0)
        self.assertEqual(r['final_state'], 'DISARMED')


if __name__ == '__main__':
    unittest.main()
