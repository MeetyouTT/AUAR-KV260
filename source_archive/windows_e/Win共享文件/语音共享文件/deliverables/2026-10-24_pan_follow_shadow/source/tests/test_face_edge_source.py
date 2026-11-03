"""Use the actual r4 face target state without creating models or a camera."""
from http.server import ThreadingHTTPServer
import http.client
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'face_edge_v5'))
sys.path.insert(0, '/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
from board.vision import ui_camera_service as camera
from board.identity.face_targets import FaceTargetService
from face_source import install, observation, STREAM_PATH
install(camera)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000]
        self.state = camera.CameraState('boot', 'service', clock=lambda: self.now[0])
        self.face = FaceTargetService(lambda: None, lambda *args: None, self.state.camera_epoch,
                                      lock=self.state.lock, clock=self.state.clock)
        self.state.identity = SimpleNamespace(face_targets=self.face, ready=False)
        self.state.captured(1000)
        self.face.ready, self.face.count, self.face.stamp = True, 1, 1000
        self.face.key = {'camera_epoch': self.state.camera_epoch, 'track_id': 1, 'track_generation': 9}
        self.face.tracker.last_frame = 7
        self.face.tracker.tracks = {1: {'visible': True, 'confirmed': True, 'frame_id': 7,
                                      'observed_time': 1., 'box': [120., 100., 80., 80.], 'score': .95}}

    def test_face_coordinates_are_independent_of_sface_identity_readiness(self):
        p = observation(self.state)
        self.assertEqual(p['state'], 'READY')
        self.assertEqual(p['target_kind'], 'face')
        self.assertEqual(p['target']['box'], [120., 100., 80., 80.])
        self.assertEqual(p['target']['track_generation'], 9)
        self.assertEqual(p['source_mono_ms'], 1000)
        self.assertEqual(self.face.interval, 100)
        self.assertEqual(self.face.ttl, 1000)
        self.assertNotIn('identity', p)
        self.assertNotIn('landmarks', p)

    def test_long_ui_ttl_does_not_extend_motor_source_freshness(self):
        self.now[0] = 1250
        self.state.captured(1250)
        self.assertIsNotNone(self.face.current_target())
        self.assertEqual(observation(self.state)['state'], 'EXPIRED')
        self.assertEqual(observation(self.state)['source_mono_ms'], 1000)

    def test_detection_time_counts_toward_period_without_changing_retry_recovery(self):
        for elapsed, expected in ((.065, 35.), (.14, 0.)):
            with patch.object(FaceTargetService, '_process_with_retry', return_value='done'):
                face = FaceTargetService(lambda: None, lambda *args: None, 'camera',
                                         slot_retry=True, retry_recovery_ms=50)
            with patch('face_source.time.monotonic', side_effect=[1., 1.+elapsed]):
                self.assertEqual(face._process_with_retry(None, None), 'done')
            self.assertAlmostEqual(face.interval, expected)
            self.assertEqual(face.retry_recovery_ms, 50)
            self.assertEqual(face.ttl, 1000)

    def test_multiple_or_unmeasured_face_never_exports_target(self):
        self.face.count = 2
        self.assertEqual(observation(self.state)['state'], 'MULTIPLE_FACES')
        self.face.count = 1
        self.face.tracker.tracks[1]['frame_id'] = 8
        p = observation(self.state)
        self.assertEqual(p['state'], 'INCONSISTENT_FACE_SOURCE')
        self.assertIsNone(p['target'])

    def test_optical_flow_is_fresh_pixel_measurement_with_bounded_face_anchor(self):
        value=dict(frame_id=8,stamp=1200,anchor_stamp=1000,key=self.face.key,
                   box=[125.,100.,80.,80.],score=.95)
        self.face._edge_flow=SimpleNamespace(snapshot=lambda:(value,''),diagnostics=lambda:{'reason':'MEASURED'})
        self.now[0]=1220;self.state.captured(1200)
        p=observation(self.state)
        self.assertEqual(p['state'],'READY');self.assertEqual(p['source_mono_ms'],1200)
        self.assertEqual(p['face_detection_mono_ms'],1000)
        self.assertEqual(p['measurement_method'],'face_region_template_match')
        self.face.count=2
        self.assertEqual(observation(self.state)['state'],'MULTIPLE_FACES')
        self.face.count=1;self.now[0]=2000;self.state.captured(2000);value['stamp']=2000
        self.assertEqual(observation(self.state)['state'],'EXPIRED')

    def test_real_http_stream_uses_face_contract(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), camera.handler_for(self.state))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        c = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=1)
        try:
            c.request('GET', STREAM_PATH+'?duration_ms=50')
            r = c.getresponse()
            self.assertEqual(r.status, 200)
            self.assertEqual(json.loads(r.readline(8193)), observation(self.state))
            r.read()
        finally:
            c.close()
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
