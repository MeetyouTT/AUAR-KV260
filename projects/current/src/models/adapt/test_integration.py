"""Regression checks against the recovered camera/identity implementation."""
import sys
import threading
import unittest
from types import SimpleNamespace
import board.identity
import board.vision
board.identity.__path__[:0] = ['/candidate/board/identity', '/live/board/identity']
board.vision.__path__[:0] = ['/candidate/board/vision', '/live/board/vision']
from board.identity.face_targets import FaceTargetService
from board.vision.dpu_vision_runtime import SlotUnavailable
from board.vision.dpu_yunet import DpuYuNet
from board.vision.ui_camera_service import CameraState


class IntegrationTests(unittest.TestCase):
    def test_skipped_frame_preserves_binding_and_expires_by_existing_ttl(self):
        now = [1000]
        callbacks = []
        service = FaceTargetService(None, lambda *x: callbacks.append(x), 'epoch', clock=lambda: now[0])
        key = {'camera_epoch': 'epoch', 'track_id': 1, 'track_generation': 1}
        service.key, service.ready, service.stamp = key, True, 1000
        def unavailable(_):
            raise SlotUnavailable('deadline')
        service.process((object(), 1, 1000), SimpleNamespace(detect=unavailable))
        self.assertEqual(service.current_target(), key)
        self.assertEqual(service.discarded, 1)
        self.assertEqual(callbacks, [])
        now[0] = 2000
        self.assertIsNone(service.current_target())

    def test_worker_closes_model_on_exit(self):
        constructed, closed = threading.Event(), threading.Event()
        class FakeDetector:
            def __init__(self):
                constructed.set()
            def close(self):
                closed.set()
        service = FaceTargetService(FakeDetector, lambda *_: None, 'epoch')
        service.start()
        self.assertTrue(constructed.wait(1))
        service.close()
        self.assertTrue(closed.is_set())

    def test_over_budget_dpu_task_falls_back_to_cpu_without_changing_result(self):
        detector = DpuYuNet.__new__(DpuYuNet)
        detector.schedule = SimpleNamespace(disabled=lambda kind: True)
        detector.fallback = SimpleNamespace(detect=lambda image: ('cpu-result', image))
        result = detector.detect('frame')
        self.assertEqual(result, ('cpu-result', 'frame'))
        self.assertEqual(detector.kind, 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')

    def test_camera_health_exposes_real_schedule_counters(self):
        state = CameraState('boot', clock=lambda: 1000)
        state.dpu_schedule = SimpleNamespace(health=lambda: {'primary_calls': 17})
        self.assertEqual(state.health()['dpu_schedule'], {'primary_calls': 17})
        self.assertFalse(state.health()['motion_command_emitted'])


if __name__ == '__main__':
    unittest.main()
