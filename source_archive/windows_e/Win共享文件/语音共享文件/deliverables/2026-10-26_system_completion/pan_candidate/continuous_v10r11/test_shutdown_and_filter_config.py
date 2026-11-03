import math
import time
import unittest
from types import SimpleNamespace

from continuous_face_control import EdgeConfig,FaceEdgeController
from one_euro import OneEuroFilter
from safe_shutdown import stop_then_close_stream


class ShutdownAndFilterTests(unittest.TestCase):
    def test_stop_is_called_before_blocking_reader_cleanup(self):
        events=[]
        def stop():events.append(('stop',time.monotonic()));return {'stopped':True}
        def close():events.append(('reader',time.monotonic()));time.sleep(.12)
        result=stop_then_close_stream(SimpleNamespace(close=stop),SimpleNamespace(close=close))
        self.assertEqual([x[0] for x in events],['stop','reader'])
        self.assertLess(events[1][1]-events[0][1],.05)
        self.assertTrue(result['stopped'])

    def test_stop_failure_still_closes_reader_and_is_not_masked(self):
        events=[]
        def stop():events.append('stop');raise RuntimeError('primary STOP failure')
        def close():events.append('reader');raise ValueError('secondary reader failure')
        with self.assertRaisesRegex(RuntimeError,'primary STOP failure'):
            stop_then_close_stream(SimpleNamespace(close=stop),SimpleNamespace(close=close))
        self.assertEqual(events,['stop','reader'])

    def test_reader_error_happens_after_stop(self):
        events=[]
        def stop():events.append('stop');return {}
        def close():events.append('reader');raise ValueError('reader failure')
        with self.assertRaises(ValueError):stop_then_close_stream(SimpleNamespace(close=stop),SimpleNamespace(close=close))
        self.assertEqual(events,['stop','reader'])

    def test_default_filters_preserve_old_effective_one_hz_behavior(self):
        controller=FaceEdgeController('boot',1469)
        reference=OneEuroFilter()
        width_reference=OneEuroFilter(beta=2.)
        for i,value in enumerate((.5,.51,.49,.53,.48,.52),1):
            self.assertEqual(controller.center_filter(value,i*.1),reference(value,i*.1))
            self.assertEqual(controller.width_filter(value,i*.1),width_reference(value,i*.1))

    def test_explicit_position_tau_changes_filtered_position(self):
        values=[]
        for tau in (30.,500.):
            controller=FaceEdgeController('boot',1469,config=EdgeConfig(filter_tau_ms=tau))
            values.append([controller.center_filter(value,i*.1) for i,value in enumerate((.5,.52,.49,.53,.48),1)])
        self.assertNotEqual(values[0],values[1])

    def test_explicit_derivative_tau_changes_velocity_feedback(self):
        values=[]
        for tau in (30.,300.):
            controller=FaceEdgeController('boot',1469,config=EdgeConfig(velocity_filter_tau_ms=tau))
            row=[]
            for i,value in enumerate((.5,.52,.49,.53,.48),1):
                controller.center_filter(value,i*.1);row.append(controller.center_filter.derivative_ratio_s)
            values.append(row)
        self.assertNotEqual(values[0],values[1])


if __name__=='__main__':unittest.main()
