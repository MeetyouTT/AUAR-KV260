import unittest
from dataclasses import replace
import test_continuous_session as fixtures
from continuous_face_control import EdgeConfig,FaceEdgeController


class EffectiveFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.SessionTests.setUpClass()
    def outputs(self,config):
        f=fixtures.SessionTests();f.setUp();control=FaceEdgeController('boot',1469,config=config)
        result=[]
        for center in [.5]*8+[.5+i*.01 for i in range(20)]:
            result.append(control.observe(f.packet(center),int(f.now*1000),allow_fixture=True))
            f.now+=.08
        return [r['filtered_center_ratio'] for r in result],control.status()
    def test_real_filter_parameter_changes_output(self):
        slow,_=self.outputs(EdgeConfig(one_euro_min_cutoff_hz=.5,one_euro_beta=0.))
        fast,status=self.outputs(EdgeConfig(one_euro_min_cutoff_hz=5.,one_euro_beta=10.))
        self.assertGreater(fast[-1],slow[-1]);self.assertEqual(status['effective_filter']['beta'],10.)
    def test_legacy_time_fields_are_explicitly_inactive(self):
        a,_=self.outputs(EdgeConfig(filter_tau_ms=30,velocity_filter_tau_ms=30))
        b,status=self.outputs(EdgeConfig(filter_tau_ms=500,velocity_filter_tau_ms=300))
        self.assertEqual(a,b);self.assertFalse(status['legacy_filter_tau_parameters_active'])
        self.assertFalse(status['median_used_for_control'])
    def test_invalid_effective_parameters_are_rejected(self):
        for name,value in [('one_euro_beta',-1),('one_euro_min_cutoff_hz',0),
                           ('one_euro_derivative_cutoff_hz',float('nan')),('one_euro_width_beta',True)]:
            with self.assertRaises(ValueError):replace(EdgeConfig(),**{name:value})
