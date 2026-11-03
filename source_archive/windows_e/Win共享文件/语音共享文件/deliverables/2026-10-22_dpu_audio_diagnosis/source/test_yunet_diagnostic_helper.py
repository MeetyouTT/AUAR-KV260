import ast,copy
from pathlib import Path
import unittest

SOURCE=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_yunet_diagnostic_20261022_v2.py')
ns={'__name__':'_diagnostic_test'}
exec(compile(SOURCE.read_text(),str(SOURCE),'exec'),ns)


class DiagnosticHelperTests(unittest.TestCase):
    def report(self):
        return {'samples':[{'detected_frames':10,'dpu_schedule':{'optional':{'yunet':{'calls':3}}}}],
            'camera_after':{'detected_frames':1210,'dpu_schedule':{'optional':{'yunet':{'calls':303}}},
                'pipeline_metrics':{'stages':{'yunet.execute_wait':{'count':300}}},'shadow':None},
            'observation_elapsed_s':120.,'usb_audio_warning_count':0}

    def test_short_diagnostic_result_never_promotes_formal_or_long_run(self):
        report=self.report();ns['validate_diagnostic'](report)
        self.assertTrue(report['passed']);self.assertFalse(report['formal_identity_or_long_run_accepted'])
        self.assertEqual(report['observed_yolo_hz'],10)

    def test_no_computation_or_new_warning_or_unexpected_shadow_refused(self):
        report=self.report();report['camera_after']['pipeline_metrics']['stages']['yunet.execute_wait']['count']=0
        with self.assertRaises(AssertionError):ns['validate_diagnostic'](report)
        report=self.report();report['usb_audio_warning_count']=1
        with self.assertRaises(AssertionError):ns['validate_diagnostic'](report)
        report=self.report();report['camera_after']['shadow']={'enabled':True}
        with self.assertRaises(AssertionError):ns['validate_diagnostic'](report)

    def test_duration_and_primary_rate_gates(self):
        report=self.report();report['observation_elapsed_s']=119
        with self.assertRaises(AssertionError):ns['validate_diagnostic'](report)
        report=self.report();report['camera_after']['detected_frames']=1000
        with self.assertRaises(AssertionError):ns['validate_diagnostic'](report)

    def test_exact_four_source_overlay_and_original_guards(self):
        self.assertEqual(len(ns['OVERLAY']),4)
        self.assertTrue(all(p.startswith('board/vision/') for p in ns['OVERLAY']))
        self.assertEqual(ns['UNIT_SHA'],'84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c')
        source=SOURCE.read_text();ast.parse(source)
        self.assertIn("'--on-active=360s'",source)
        self.assertIn('AURA_DPU_DIAGNOSTICS=1',source)
        self.assertIn("report['latest_camera_seen']=state;healthy(state)",source)
        self.assertNotIn("identity['dpu_sface_shadow']=",source)


if __name__=='__main__':unittest.main(verbosity=2)
