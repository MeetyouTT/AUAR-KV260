"""Transport tests use the exact r4 CameraState, with fixture observations only."""
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'stream_v2'))
sys.path.insert(0, '/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
from board.vision import ui_camera_service as camera
from board.motion.camera_feed import install as install_feed, observation
from motion_stream import install, PATH

install_feed(camera)
install(camera)


def source(fid=1, stamp=1000):
    return {'target_id': 1, 'tracks': [
        {'track_id': 1, 'generation': 1, 'visible': True, 'confirmed': True,
         'frame_id': fid, 'captured_at': stamp/1000., 'box': [200., 0., 80., 480.], 'score': .9}]}


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000]
        self.state = camera.CameraState('fixture-boot', 'fixture-service', clock=lambda: self.now[0])
        self.state.captured(1000)
        self.state.observed(1, 1000, source(), 1.)

    def serve(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), camera.handler_for(self.state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=1)
        self.addCleanup(connection.close)
        return connection

    def test_stream_matches_source_contract_and_preserves_existing_routes(self):
        c = self.serve()
        c.request('GET', PATH+'?duration_ms=100')
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        first = json.loads(r.readline(8193))
        self.assertEqual(first, observation(self.state))
        self.assertEqual(first['source_mono_ms'], 1000)
        self.assertNotIn('identity', first)
        self.assertNotIn('image', first)
        r.read()
        c.close()
        c.request('GET', '/health')
        self.assertEqual(c.getresponse().status, 200)

    def test_publish_notification_delivers_new_source_without_restamping(self):
        c = self.serve()
        c.request('GET', PATH+'?duration_ms=300')
        r = c.getresponse()
        r.readline(8193)
        self.now[0] = 1100
        self.state.captured(1100)
        self.state.observed(2, 1100, source(2, 1100), 1.)
        packets = [json.loads(r.readline(8193)) for _ in range(2)]
        self.assertTrue(any(p['source_frame_id'] == 2 and p['source_mono_ms'] == 1100 for p in packets))

    def test_frozen_source_expires_in_heartbeat_without_refreshing_timestamp(self):
        c = self.serve()
        c.request('GET', PATH+'?duration_ms=300')
        r = c.getresponse()
        r.readline(8193)
        self.now[0] = 1300
        packets = [json.loads(r.readline(8193)) for _ in range(3)]
        self.assertTrue(any(p['state'] == 'EXPIRED' for p in packets))
        self.assertTrue(all(p['source_mono_ms'] == 1000 for p in packets))

    def fake_handler(self, writer, duration=200):
        h = object.__new__(camera.handler_for(self.state))
        h.path = PATH+'?duration_ms='+str(duration)
        h.connection = SimpleNamespace(settimeout=lambda _: None)
        h.send_response = h.end_headers = lambda *args: None
        h.send_header = lambda *args: None
        h.respond = lambda code, value: setattr(h, 'rejected', code)
        h.wfile = writer
        return h

    def test_slow_consumer_never_blocks_observation_publisher(self):
        entered, release, published = threading.Event(), threading.Event(), threading.Event()
        def blocked_write(_):
            entered.set()
            release.wait(1)
            raise TimeoutError('fixture slow consumer')
        h = self.fake_handler(SimpleNamespace(write=blocked_write, flush=lambda: None))
        t = threading.Thread(target=h.do_GET)
        t.start()
        self.assertTrue(entered.wait(1))
        def publish():
            self.state.observed(2, 1100, source(2, 1100), 1.)
            published.set()
        p = threading.Thread(target=publish)
        p.start()
        try:
            self.assertTrue(published.wait(.3))
            second = self.fake_handler(SimpleNamespace(write=lambda _: None, flush=lambda: None))
            second.do_GET()
            self.assertEqual(second.rejected, 409)
        finally:
            release.set()
            t.join(1)
            p.join(1)
        self.assertFalse(self.state._motion_stream_lock.locked())

    def test_invalid_duration_is_rejected_and_install_is_idempotent(self):
        current = camera.CameraState.observed
        install(camera)
        self.assertIs(camera.CameraState.observed, current)
        h = self.fake_handler(SimpleNamespace(write=lambda _: None, flush=lambda: None), 10001)
        h.do_GET()
        self.assertEqual(h.rejected, 400)


if __name__ == '__main__':
    unittest.main()
