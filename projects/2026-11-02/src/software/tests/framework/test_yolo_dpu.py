"""Model integrity, person geometry and UI freshness without DPU hardware."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from board.interaction.ui_contract import validate_action, validate_snapshot
from board.vision.reference_core import FaceTracks
from board.vision.ui_camera_service import CameraState, PersonPreviewTracks, detector_info
from board.vision.yolo_dpu import DpuYoloX, checked_file, original_person_boxes
from common.contracts import Detection


class YoloDpuTests(unittest.TestCase):
    def test_wrong_component_hash_stops_before_native_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'model.xmodel'
            p.write_bytes(b'changed model')
            with patch('board.vision.yolo_dpu.ctypes.CDLL') as native:
                with self.assertRaisesRegex(RuntimeError, 'hash mismatch'):
                    DpuYoloX({'model': str(p), 'model_sha256': '0' * 64})
                native.assert_not_called()
            self.assertEqual(checked_file(p, hashlib.sha256(p.read_bytes()).hexdigest()), p.resolve())

    def test_native_original_coordinates_clip_without_second_scaling(self):
        people = original_person_boxes([[-20, 15, 700, 500, .8, 0], [10, 20, 30, 50, .29, 0]], 640, 480)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].box, (0., 15., 640., 465.))
        self.assertEqual(people[0].label, 'person')

    def test_bad_native_data_cannot_become_person_evidence(self):
        for row in [[0, 0, 10, 10, float('nan'), 0], [0, 0, 10, 10, .8, 2], [0, 0, 10, 10, 2, 0], [0] * 5]:
            with self.assertRaises(RuntimeError):
                original_person_boxes([row], 640, 480)
        self.assertEqual(original_person_boxes([[700, 0, 710, 10, .8, 0]], 640, 480), [])

    def test_person_output_is_bounded_and_keeps_highest_scores(self):
        people = original_person_boxes([[i*20, 0, i*20+10, 10, .3 + i / 100, 0] for i in range(30)], 640, 480)
        self.assertEqual(len(people), 16)
        self.assertGreater(people[0].score, people[-1].score)

    def test_nested_duplicate_boxes_count_as_one_person(self):
        people = original_person_boxes([[10, 20, 110, 220, .8, 0], [15, 25, 105, 215, .4, 0],
                                       [300, 20, 400, 220, .7, 0]], 640, 480)
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].score, .8)

    def state(self):
        self.now = 1000
        info = detector_info({'detector_backend': 'dpu_yolox', 'yolo': {'model_sha256': 'a' * 64, 'arch_fingerprint': 'fingerprint'}})
        return CameraState('boot', 'service', clock=lambda: self.now, detector_info=info)

    def test_dpu_ready_requires_fresh_real_camera_inference(self):
        state = self.state()
        self.assertEqual(state.snapshot()['modules']['npu']['state'], 'DEGRADED')
        state.captured(self.now)
        state.publish_preview(1, self.now, b'preview')
        state.observed(1, self.now, {'target_id': None, 'tracks': []}, 20)
        value = validate_snapshot(state.snapshot(), 'boot', self.now)
        self.assertEqual(value['modules']['npu']['state'], 'READY')
        self.assertEqual(value['modules']['vision']['count_kind'], 'people')
        self.assertEqual(value['modules']['vision']['people_count'], 0)
        self.now += 751
        state.captured(self.now)
        state.publish_preview(2, self.now, b'new preview')
        value = state.snapshot()
        self.assertEqual(value['modules']['npu']['state'], 'DEGRADED')
        self.assertNotIn('people_count', value['modules']['vision'])
        self.assertEqual(value['preview']['frame_id'], 2)

    def test_detector_failure_keeps_camera_preview_and_removes_target(self):
        state = self.state()
        state.captured(self.now)
        state.publish_preview(1, self.now, b'preview')
        state.detector_error = 'DPU unavailable'
        value = state.snapshot()
        self.assertEqual(value['modules']['camera']['state'], 'READY')
        self.assertEqual(value['modules']['npu']['state'], 'ERROR')
        self.assertEqual(value['modules']['target']['tracks'], [])
        self.assertEqual(state.preview(state.camera_epoch, 1), b'preview')

    def test_person_reacquisition_invalidates_previous_target_generation(self):
        state = self.state()
        tracker = PersonPreviewTracks(state.camera_epoch, FaceTracks)
        people = [Detection((10., 20., 100., 200.), .8)]
        tracker.update(people, 1, .8, 640, 480)
        old = tracker.update(people, 2, .9, 640, 480)
        state.captured(self.now)
        state.observed(2, self.now, old, 20)
        key = state.snapshot()['modules']['target']['tracks'][0]['key']
        tracker.update([], 3, 1., 640, 480)
        self.now += 100
        new = tracker.update(people, 4, 1.1, 640, 480)
        state.captured(self.now)
        state.observed(4, self.now, new, 20)
        current = state.snapshot()
        self.assertEqual(current['modules']['target']['tracks'][0]['key']['track_generation'], 2)
        with self.assertRaises(ValueError):
            validate_action('target_select', {'target': key}, current)
        self.assertTrue(current['modules']['target']['tracks'][0]['label'].startswith('人体 #'))


if __name__ == '__main__':
    unittest.main()
