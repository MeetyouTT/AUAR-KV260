"""DPU scheduling/tensor/identity rules without hardware or real face samples."""
from contextlib import contextmanager
import threading
import time
from types import SimpleNamespace
import unittest
import numpy as np

from board.vision.dpu_schedule import DpuSchedule
from board.identity.dpu_sface import DpuSFace, checked_subgraph, quantize_crop
from tests.framework.test_voice_identity import Harness
import tempfile
import json
from pathlib import Path
from board.interaction.ui_contract import ACTIONS


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.now = 1.
        self.schedule = DpuSchedule(clock=lambda: self.now)

    def ready(self):
        with self.schedule.detection(self.now+.1):pass

    def test_no_identity_until_detection_has_started(self):
        with self.schedule.identity() as acquired:self.assertFalse(acquired)

    def test_identity_uses_free_gap_and_does_not_queue_on_detection(self):
        with self.schedule.detection(self.now+.1):
            with self.schedule.identity() as acquired:self.assertFalse(acquired)
        with self.schedule.identity() as acquired:
            self.assertTrue(acquired);self.now += .008
        self.assertEqual(self.schedule.health()['identity_calls'], 1)

    def test_identity_skips_when_next_detection_is_near(self):
        self.ready();self.now += .08
        with self.schedule.identity() as acquired:self.assertFalse(acquired)

    def test_overrun_disables_future_identity_but_detection_continues(self):
        self.ready()
        with self.schedule.identity() as acquired:
            self.assertTrue(acquired);self.now += .021
        self.assertTrue(self.schedule.health()['identity_disabled'])
        self.ready()
        with self.schedule.identity() as acquired:self.assertFalse(acquired)
        self.assertEqual(self.schedule.health()['detection_calls'], 2)

    def test_exceptions_release_each_slot(self):
        with self.assertRaises(ValueError):
            with self.schedule.detection(self.now+.1):raise ValueError('fixture')
        with self.assertRaises(ValueError):
            with self.schedule.identity() as acquired:
                self.assertTrue(acquired);raise ValueError('fixture')
        self.assertIsNone(self.schedule.health()['active'])
        self.ready()

    def test_waiting_detection_wins_and_cannot_overlap_identity(self):
        gate = DpuSchedule()
        with gate.detection(time.monotonic()+1):pass
        entered = threading.Event()
        release = threading.Event()
        def detector():
            with gate.detection(time.monotonic()+1):
                entered.set();release.wait(2)
        with gate.identity() as acquired:
            self.assertTrue(acquired)
            thread = threading.Thread(target=detector);thread.start()
            end = time.monotonic()+1
            while not gate.health()['waiting_detection'] and time.monotonic() < end:time.sleep(.001)
            self.assertFalse(entered.is_set())
            with gate.identity() as second:self.assertFalse(second)
        try:
            self.assertTrue(entered.wait(1))
            with gate.identity() as second:self.assertFalse(second)
        finally:
            release.set();thread.join(2)
        self.assertFalse(thread.is_alive())


class TensorTests(unittest.TestCase):
    def test_quantization_preserves_rgb_layout_signed_rounding_and_saturation(self):
        bgr = np.zeros((112,112,3), np.uint8)
        bgr[0,0] = [0,127,255]
        actual = quantize_crop(bgr)
        self.assertEqual(actual.dtype, np.int8)
        self.assertEqual(actual.shape, (1,112,112,3))
        self.assertEqual(actual[0,0,0].tolist(), [127,0,-127])
        self.assertTrue(actual.flags.c_contiguous)

    def test_wrong_crop_dimensions_or_type_are_rejected(self):
        for bad in (None, np.zeros((112,112,3), np.float32), np.zeros((111,112,3),np.uint8)):
            with self.assertRaises(ValueError):quantize_crop(bad)

    def graph(self):
        class Tensor:
            def __init__(self, dims, fixed):self.dims, self.fixed, self.dtype = dims, fixed, 'xint8'
            def get_attr(self, key):return self.fixed
        class Sub:
            attrs = {'device': 'DPU', 'dpu_fingerprint': int('0x101000056010407',16)}
            def __init__(self):self.inputs, self.outputs = [Tensor([1,112,112,3],7)], [Tensor([1,128],5)]
            def has_attr(self, key):return key in self.attrs
            def get_attr(self, key):return self.attrs[key]
            def get_input_tensors(self):return self.inputs
            def get_output_tensors(self):return self.outputs
        sub = Sub()
        return SimpleNamespace(get_root_subgraph=lambda:SimpleNamespace(toposort_child_subgraph=lambda:[sub])), sub

    def test_exact_subgraph_fingerprint_layout_dtype_and_fixpoints_required(self):
        graph, sub = self.graph()
        self.assertIs(checked_subgraph(graph,'0x101000056010407'), sub)
        with self.assertRaises(RuntimeError):checked_subgraph(graph,'other')
        for attr, value in [('dims',[1,3,112,112]), ('fixed',6), ('dtype','float32')]:
            graph, sub = self.graph();setattr(sub.inputs[0],attr,value)
            with self.assertRaises(RuntimeError):checked_subgraph(graph,'0x101000056010407')

    def feature(self, schedule):
        class Runner:
            called = 0
            def execute_async(self, inputs, outputs):
                self.called += 1
                outputs[0][:] = np.arange(-64,64,dtype=np.int8)
                return (123,0)
            def wait(self, job):
                if job != (123,0):raise ValueError('This binding requires the tuple')
                return 0
        model = DpuSFace.__new__(DpuSFace)
        model.runner = Runner();model.schedule = schedule
        model.last_reason = '';model.last_ms = None
        return model

    def test_wait_uses_one_tuple_argument_and_output_dequantizes_by_32(self):
        gate = DpuSchedule()
        with gate.detection(time.monotonic()+1):pass
        model = self.feature(gate)
        actual = model.feature(np.zeros((112,112,3),np.uint8))
        np.testing.assert_array_equal(actual,np.arange(-64,64,dtype=np.float32)/32.)
        self.assertEqual(model.runner.called,1)

    def test_skipped_slot_never_submits_a_dpu_job(self):
        model = self.feature(DpuSchedule())
        self.assertIsNone(model.feature(np.zeros((112,112,3),np.uint8)))
        self.assertEqual(model.runner.called,0)

    def test_missing_same_process_owner_is_rejected_before_loading(self):
        with self.assertRaises(RuntimeError):DpuSFace({'arch_fingerprint':'expected'},None,'expected')
        with self.assertRaises(RuntimeError):DpuSFace({'arch_fingerprint':'expected'},DpuSchedule(),'other')


class KnownFramesTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.h = Harness(folder.name);self.addCleanup(self.h.close)
        self.h.service.known_frames = 3;self.h.service.backend = 'DPU_SFACE_INT8'
        self.h.store.enroll('one','fixture-person',(1,0,0,0),consent=True)

    def test_name_only_appears_after_three_fresh_matching_frames(self):
        for _ in range(2):
            self.h.infer()
            identity = self.h.read()['snapshot']['modules']['identity']
            self.assertEqual(identity['state'],'UNKNOWN');self.assertEqual(identity['display_name'],'')
            self.h.now += 500;self.h.frame()
        self.h.infer()
        self.assertEqual(self.h.read()['snapshot']['modules']['identity']['display_name'],'fixture-person')

    def test_duplicate_frame_does_not_satisfy_consistency(self):
        for _ in range(5):self.h.infer()
        self.assertEqual(self.h.service.known_history['count'],1)
        self.assertEqual(self.h.read()['snapshot']['modules']['identity']['display_name'],'')

    def test_target_change_and_bad_face_reset_evidence(self):
        for _ in range(3):self.h.infer();self.h.now += 500;self.h.frame()
        self.h.frame(generation=2);self.h.infer()
        self.assertEqual(self.h.service.known_history['count'],1)
        self.h.now += 500;self.h.frame();self.h.infer(vector=None)
        self.assertIsNone(self.h.service.known_history)

    def test_backend_failure_hides_name_and_disables_enrollment(self):
        self.h.service.backend_available = lambda:False
        snapshot = self.h.read()['snapshot']
        self.assertEqual(snapshot['modules']['identity']['state'],'ERROR')
        self.assertFalse(snapshot['capabilities']['identity_collect'])
        self.assertFalse(self.h.service.health()['ready'])


class SchemaConsistencyTests(unittest.TestCase):
    def test_python_actions_match_published_json_schemas(self):
        root = Path(__file__).resolve().parents[2]/'common/schemas'
        command = json.loads((root/'board_ui_command.schema.json').read_text())
        snapshot = json.loads((root/'board_ui_snapshot.schema.json').read_text())
        self.assertEqual(set(ACTIONS), set(command['properties']['action']['enum']))
        self.assertEqual(set(ACTIONS), set(snapshot['properties']['capabilities']['properties']))
        covered = []
        for branch in command['oneOf']:
            action = branch['properties']['action']
            covered.extend(action.get('enum', [action.get('const')]))
        self.assertEqual(sorted(ACTIONS), sorted(covered))

    def test_collect_and_cancel_parameter_schemas_are_explicit(self):
        path = Path(__file__).resolve().parents[2]/'common/schemas/board_ui_command.schema.json'
        command = json.loads(path.read_text())
        for branch in command['oneOf']:
            action = branch['properties']['action'];params = branch['properties']['params']
            if 'identity_collect' in action.get('enum', []):
                self.assertEqual(set(params['required']), {'target','display_name','confirmed'})
                self.assertEqual(params['properties']['confirmed'], {'const':True})
            if action.get('const') == 'identity_cancel':
                self.assertEqual(params['required'], ['enrollment_id'])
                self.assertFalse(params['additionalProperties'])


if __name__ == '__main__':unittest.main()
