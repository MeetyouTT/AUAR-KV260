"""Native business paths use the real enabled production metrics registry."""
import numpy as np
import unittest
from board.vision.pipeline_metrics import PipelineMetrics
from board.vision.native_binding import Execution
import test_native_business as base


class EnabledMetrics(unittest.TestCase):
    setUp=base.BusinessTests.setUp
    sface=base.BusinessTests.sface
    ui_inference=base.BusinessTests.ui_inference
    def test_real_enabled_metrics_accept_native_SFace_and_YuNet_timings(self):
        self.metrics=PipelineMetrics(enabled=True)
        face=self.sface()
        feature=face.feature(np.zeros((112,112,3),np.uint8),source_mono_ms=self.clock.millis())
        self.assertEqual(feature.shape,(128,))
        runner=base.pinned(self.context,self.schedule,self.metrics,1)
        original=runner.runner.execute_encoded
        def encoded_head(source,**arguments):
            result=original(source,**arguments)
            # This fixture exercises the common observer/dequantize boundary;
            # exact real four-head contracts have their separate C ABI tests.
            return Execution(result.report,(bytes(128),),result.returned_mono_ns,result.source_expires_ns)
        runner.runner.execute_encoded=encoded_head
        value=runner.execute_encoded(np.zeros((1,320,320,3),np.int8),
                                    source_expires_ns=self.clock.ns+1_000_000_000)
        self.assertIsNotNone(value)
        recorded=self.metrics.snapshot()['stages']
        for task in ['sface','yunet']:
            self.assertIn(task+'.native_lease',recorded)
            self.assertIn(task+'.python_return_after_release',recorded)

    def test_actual_UI_deadline_rejection_with_real_enabled_metrics_survives(self):
        self.metrics=PipelineMetrics(enabled=True)
        original=self.context.execute_yolo;calls=[]
        def execute(image,**arguments):
            calls.append(arguments)
            if len(calls)==1:
                report=self.context.report(0,arguments['source_expires_ns'])
                report.update(outcome=1,submitted=0,completed=0,business_ready=0)
                return Execution(report,(),self.clock.ns,arguments['source_expires_ns'])
            return original(image,**arguments)
        self.context.execute_yolo=execute
        namespace,state,observations,owner=self.ui_inference(self.context)
        self.assertEqual(observations,[2]);self.assertEqual(len(calls),2)
        self.assertEqual(state.native_primary_deferred,1)
        self.assertIs(namespace['detector'],owner)
        self.assertNotIn('yolo.native_source_or_deadline_deferred',self.metrics.snapshot()['stages'])
