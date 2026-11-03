import importlib.util
import json
from pathlib import Path
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('metrics',ROOT/'candidate/aura/board/vision/pipeline_metrics.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class MetricsTests(unittest.TestCase):
    def test_disabled_does_not_allocate_or_keep_values(self):
        m=module.PipelineMetrics()
        m.value('not-a-stage',object());m.elapsed('not-a-stage',None)
        self.assertEqual(m.stages,{})
        self.assertEqual(m.snapshot(),{'enabled':False})

    def test_recent_quantiles_bounded_and_distinct_from_lifetime_mean(self):
        m=module.PipelineMetrics(enabled=True,capacity=16)
        for n in range(100):m.value('yolo.path',n)
        result=m.snapshot()['stages']['yolo.path']
        self.assertEqual(result['count'],100);self.assertEqual(result['recent_count'],16)
        self.assertEqual(result['mean_ms'],49.5);self.assertEqual(result['recent_p50_ms'],91.)
        self.assertEqual(len(m.stages['yolo.path']['recent']),16)
        self.assertEqual(result['min_ms'],0);self.assertEqual(result['max_ms'],99)

    def test_invalid_data_cannot_add_unknown_stages_or_nonfinite_json(self):
        m=module.PipelineMetrics(enabled=True)
        for stage,value in [('unknown',1),('yolo.path',float('nan')),('yolo.path',-1),('yolo.path',True)]:
            with self.assertRaises(ValueError):m.value(stage,value)
        self.assertEqual(m.stages,{})
        json.dumps(m.snapshot(),allow_nan=False)

    def test_concurrent_updates_and_snapshot_do_not_lose_counts(self):
        m=module.PipelineMetrics(enabled=True,capacity=16)
        def write():
            for n in range(2000):m.value('sface.execute_wait',n/100)
        threads=[threading.Thread(target=write) for _ in range(4)]
        for thread in threads:thread.start()
        for _ in range(20):json.dumps(m.snapshot(),allow_nan=False)
        for thread in threads:thread.join()
        row=m.snapshot()['stages']['sface.execute_wait']
        self.assertEqual(row['count'],8000);self.assertEqual(row['recent_count'],16)

    def test_snapshot_does_not_expose_mutable_internal_buffers(self):
        m=module.PipelineMetrics(enabled=True);m.value('yolo.path',10)
        result=m.snapshot();result['stages']['yolo.path']['count']=999
        self.assertEqual(m.snapshot()['stages']['yolo.path']['count'],1)
        self.assertNotIn('recent',m.snapshot()['stages']['yolo.path'])


if __name__=='__main__':unittest.main(verbosity=2)
