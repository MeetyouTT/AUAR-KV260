from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import board.vision
METRICS_ROOT=Path('/implementation/candidate/aura')
board.vision.__path__[:0]=[str(METRICS_ROOT/'board/vision'),'/previous/candidate/aura/board/vision','/live/board/vision']
from board.vision.dpu_vision_runtime import PinnedRunner, sface_feature
from board.vision.pipeline_metrics import PipelineMetrics
from board.vision.ui_camera_service import CameraState


class MeasuredRunnerTests(unittest.TestCase):
    def runner(self):
        gate={'active':False,'jobs':0}
        class Metrics(PipelineMetrics):
            def value(metrics,stage,value):
                self.assertFalse(gate['active'],'Metric aggregation must not hold admitted optional DPU interval')
                super().value(stage,value)
        class Output:
            dims=[1,128]
            name='features'
            def get_attr(self,name):return 5
        class Native:
            def execute_async(self,inputs,outputs):
                self_test.assertTrue(gate['active']);gate['jobs']+=1
                outputs[0].fill(16)
                return 1
            def wait(self,job):return 0
        self_test=self
        runner=PinnedRunner.__new__(PinnedRunner)
        runner.owner=SimpleNamespace(ownership=SimpleNamespace(fileno=lambda:10))
        runner.runner=Native();runner.inputs=[SimpleNamespace(dims=[1,112,112,3])]
        runner.outputs=[Output()];runner.metrics=Metrics(enabled=True)
        runner.stage_kind='sface';runner.last_ms=None
        return runner,gate

    def test_actual_encoded_output_and_metrics_after_slot_release(self):
        runner,gate=self.runner()
        @contextmanager
        def slot():
            gate['active']=True
            try:yield True
            finally:gate['active']=False
        result=runner.execute_encoded(np.zeros((1,112,112,3),np.int8),slot=slot())
        np.testing.assert_array_equal(result['features'],np.full((1,128),.5,np.float32))
        self.assertEqual(gate['jobs'],1)
        rows=runner.metrics.snapshot()['stages']
        self.assertEqual(set(rows),{'sface.allocate','sface.slot_wait','sface.execute_wait','sface.dequantize'})
        self.assertTrue(all(row['count']==1 for row in rows.values()))

    def test_denial_never_executes_or_counts_completed_stage(self):
        runner,gate=self.runner()
        @contextmanager
        def slot():yield False
        self.assertIsNone(runner.execute_encoded(np.zeros((1,112,112,3),np.int8),slot=slot()))
        self.assertEqual(gate['jobs'],0)
        self.assertNotIn('sface.execute_wait',runner.metrics.snapshot()['stages'])

    def test_bad_input_fails_before_allocating_or_timing(self):
        runner,gate=self.runner()
        with self.assertRaises(ValueError):runner.execute_encoded(np.zeros((1,112,112,3),np.float32))
        self.assertEqual(gate['jobs'],0);self.assertEqual(runner.metrics.stages,{})

    def test_sface_normalization_and_feature_unchanged(self):
        runner,gate=self.runner()
        crop=np.zeros((112,112,3),np.uint8);crop[:,:,0]=255
        received=[]
        def execute(source):
            received.append(source.copy())
            return {'features':np.ones((1,128),np.float32)}
        vector=sface_feature(crop,runner,execute)
        self.assertEqual(vector.shape,(128,))
        np.testing.assert_array_equal(received[0][0,0,0],[-127.5/128,-127.5/128,127.5/128])
        self.assertIn('sface.normalize_input',runner.metrics.snapshot()['stages'])
        self.assertIn('sface.validate_output',runner.metrics.snapshot()['stages'])

    def test_camera_metrics_default_off_and_explicit_environment(self):
        with patch.dict(os.environ,{'AURA_PIPELINE_METRICS':'0'}):
            state=CameraState('boot',clock=lambda:1000)
            self.assertEqual(state.health()['pipeline_metrics'],{'enabled':False})
        with patch.dict(os.environ,{'AURA_PIPELINE_METRICS':'1'}):
            state=CameraState('boot',clock=lambda:1000)
            state.pipeline_metrics.value('capture.callback_prepare',1.5)
            self.assertEqual(state.health()['pipeline_metrics']['stages']['capture.callback_prepare']['count'],1)
            self.assertFalse(state.health()['motion_command_emitted'])


if __name__=='__main__':unittest.main(verbosity=2)
