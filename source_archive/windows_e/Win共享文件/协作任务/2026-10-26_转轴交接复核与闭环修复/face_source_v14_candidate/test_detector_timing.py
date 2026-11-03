import threading,unittest
from types import SimpleNamespace
from unittest.mock import patch
from face_timing import install


class DetectorTimingTests(unittest.TestCase):
    def service(self):
        class Service:
            def __init__(self):
                self.lock=threading.RLock();self.tracker=SimpleNamespace(last_frame=0)
                self.count=0;self.stamp=None
            def process(self,packet,detector,**kwargs):
                self.tracker.last_frame,self.stamp=packet[1:];self.count=1
                if detector.error:raise ValueError('original-failure')
                if detector.report is not None:detector.runner.last_report=dict(detector.report)
                return 'result'
        install(Service);return Service()

    def test_source_id_native_lease_and_total_are_correlated_without_pure_dpu_claim(self):
        s=self.service();detector=SimpleNamespace(error=False,runner=SimpleNamespace(last_report={}),
            report=dict(task=1,submitted=1,completed=1,start_ns=1_010_000_000,
                        native_return_ns=1_014_000_000,release_decision_ns=1_015_000_000,
                        after_unlock_ns=1_016_000_000))
        with patch('face_timing.time.monotonic_ns',side_effect=[1_000_000_000,1_030_000_000]):
            self.assertEqual(s.process(('image',7,990),detector),'result')
        record=s._edge_latest_detector_timing
        self.assertEqual(record['frame_id'],7);self.assertEqual(record['input_source_age_ms'],10)
        self.assertEqual(record['before_native_start_ms'],10)
        self.assertEqual(record['native_lease_ms'],5)
        self.assertEqual(record['after_native_release_ms'],15)
        self.assertEqual(record['process_return_source_age_ms'],40)

    def test_old_native_report_is_not_reused_for_denied_or_cpu_round(self):
        s=self.service();d=SimpleNamespace(error=False,runner=SimpleNamespace(last_report={'start_ns':1}),report=None)
        s.process(('image',8,1000),d)
        self.assertNotIn('native',s._edge_latest_detector_timing)
        self.assertEqual(s._edge_detector_timed_rounds,1)

    def test_original_exception_survives_best_effort_diagnostics(self):
        s=self.service();d=SimpleNamespace(error=True,runner=None,report=None)
        with self.assertRaisesRegex(ValueError,'original-failure'):
            s.process(('image',9,1000),d)
