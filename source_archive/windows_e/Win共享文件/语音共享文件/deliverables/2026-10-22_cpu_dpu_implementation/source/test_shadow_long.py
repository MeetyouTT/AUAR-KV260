import ast
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('longrun',ROOT/'board_shadow_long.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def state(elapsed,face,completed):
    return {'elapsed_s':elapsed,'face_count':face,'detected_frames':round(elapsed*10),
        'dpu_schedule':{'optional':{'yunet':{'calls':round(elapsed*2)}}},
        'shadow':{'accepted':completed,'execution':{'completed':completed},
            'same_crop_cosine':{'count':0},'templates_written':0,'identity_decisions_from_shadow':0,
            'failures':0,'stale':0}}


def report(face=1):
    samples=[state(i*5,face,i*3 if face else 0) for i in range(361)]
    return {'samples':samples,'camera_after':samples[-1],'observation_elapsed_s':1800,
            'baseline_observed_yolo_hz':10.,'usb_audio_warning_count':0}


class LongRunTests(unittest.TestCase):
    def test_zero_face_run_is_insufficient_not_passed(self):
        value=report(0);module.validate_observation(value)
        self.assertFalse(value['passed']);self.assertEqual(value['observation_status'],'INSUFFICIENT_FACE_COVERAGE')

    def test_deltas_ignore_before_observation_completions(self):
        value=report()
        for sample in value['samples']:
            sample['shadow']['accepted']+=100;sample['shadow']['execution']['completed']+=100
        module.validate_observation(value)
        self.assertTrue(value['passed']);self.assertEqual(value['shadow_completed'],1080)

    def test_coverage_requires_both_interval_endpoints(self):
        samples=[state(0,1,0),state(5,0,3),state(10,1,6),state(15,1,9)]
        cov=module.coverage(samples)
        self.assertEqual(cov['sampled_single_face_seconds'],5)
        self.assertEqual(cov['sface_completed_in_covered_intervals'],3)

    def test_primary_and_completion_rate_gates_are_independent(self):
        value=report();value['camera_after']['detected_frames']=16000
        module.validate_observation(value);self.assertFalse(value['passed'])
        value=report()
        for sample in value['samples']:
            sample['shadow']['accepted']=sample['shadow']['execution']['completed']=round(sample['elapsed_s']*.2)
        module.validate_observation(value)
        self.assertEqual(value['shadow_completed'],360);self.assertFalse(value['passed'])

    def test_rejected_stale_is_not_published_and_not_computation_failure(self):
        value=report();value['camera_after']['shadow']['stale']=2
        module.validate_observation(value)
        self.assertTrue(value['passed']);self.assertEqual(value['stale_results_rejected'],2)
        for field in ['templates_written','identity_decisions_from_shadow','failures']:
            value=report();value['camera_after']['shadow'][field]=1
            module.validate_observation(value);self.assertFalse(value['passed'],field)

    def test_generated_launcher_has_timeout_and_always_restore(self):
        body=(ROOT/'board_shadow_long.py').read_text();ast.parse(body)
        self.assertIn("'--on-active=2220s'",body)
        self.assertIn("report['rollback_verified']=True",body)
        self.assertIn("'--no-block','aura-camera-ui.service'",body)
        self.assertNotIn('xdputil',body)
        self.assertIn("'-p','FragmentPath','--value'",body)
        self.assertNotIn("Path('/etc/systemd/system/xserver-nodm.service')",body)
        self.assertIn("report['latest_camera_seen']=state;healthy(state,True)",body)
        self.assertIn("assert audio_warnings(baseline_cursor)==0",body)
        library=Path('/home/ghmd/aura-sface-shadow-candidate-20261021/deploy-preparation/board_shadow_pilot.py').read_text().split('\ndef main():',1)[0]
        ns={};exec(compile(library,'pinned-library','exec'),ns)
        rollback=ns['rollback_source'](Path('/controlled-test'))
        ast.parse(rollback)
        self.assertIn("assert unit.read_bytes() in (old,new)",rollback)


if __name__=='__main__':unittest.main(verbosity=2)
