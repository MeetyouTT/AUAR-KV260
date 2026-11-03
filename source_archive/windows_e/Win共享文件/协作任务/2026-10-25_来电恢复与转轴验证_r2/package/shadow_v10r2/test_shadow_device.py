import hashlib,json,subprocess,sys,unittest
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE));sys.path.insert(1,str(HERE.parent))
from shadow_device import ShadowDevice
from continuous_session import ContinuousSession
from continuous_face_control import EdgeConfig
from trajectory import Trajectory
from common.motion_observation import PROTOCOL


class ShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=HERE.parent/'ps_trajectory_v1/libaura_trajectory_compat_host.so'
        cls.trajectory=Trajectory(p,hashlib.sha256(p.read_bytes()).hexdigest())
    def setUp(self):
        self.now=10.;self.device=ShadowDevice(1500,clock=lambda:self.now)
        self.s=ContinuousSession(self.device,'boot',EdgeConfig(left_ratio=.1),lambda p:SimpleNamespace(reference_us=p),
            trajectory=self.trajectory,clock=lambda:self.now)
        self.fid=0
    def image(self,center):
        self.fid+=1;stamp=int(self.now*1000)
        packet=dict(protocol_version=PROTOCOL,source_kind='actual',target_kind='face',board_boot_id='boot',
            service_epoch='service',camera_epoch='camera',state='READY',source_frame_id=self.fid,source_mono_ms=stamp,
            face_detection_mono_ms=stamp-100,deadline_mono_ms=stamp+250,frame_width=640,frame_height=480,mirror_horizontal=True,
            target=dict(track_id=1,track_generation=1,box=[center*640-40,100.,80.,80.],score=.95))
        self.s.step(packet)
        for _ in range(4):self.now+=.02;self.s.tick()
    def test_actual_face_contract_drives_only_virtual_commands(self):
        for _ in range(30):self.image(.85)
        self.assertGreater(self.device.commits,0);self.assertEqual(self.device.arms,1)
        self.assertTrue(all(1500<=r['target_us']<=1503 for r in self.device.commands))
        self.assertFalse(self.s.fatal)
        self.assertTrue(all(r['deadline_mono_ms']<=r['effective_source_deadline_mono_ms'] for r in self.device.commands))
    def test_inside_has_no_virtual_arm_or_commit(self):
        for _ in range(30):self.image(.5)
        self.assertEqual(self.device.arms,0);self.assertEqual(self.device.commits,0)
    def test_source_disappearance_ends_virtual_permission(self):
        for _ in range(20):self.image(.85)
        for _ in range(16):self.now+=.02;self.s.tick()
        self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
    def test_target_outside_bounds_or_step_is_rejected_without_record(self):
        self.device.confirm_and_arm(SimpleNamespace(reference_us=1500),1,1,authorized=True);self.now+=.05
        for target in [1399,1601,1505,True]:
            with self.assertRaises(ValueError):self.device.submit(target,self.now)
        self.assertEqual(self.device.commands,[])
    def test_reference_and_post_arm_checks_are_not_skipped_in_shadow(self):
        with self.assertRaises(ValueError):ShadowDevice(1300)
        with self.assertRaises(ValueError):self.device.confirm_and_arm(SimpleNamespace(reference_us=1500),1,1)
        self.device.confirm_and_arm(SimpleNamespace(reference_us=1500),1,1,authorized=True)
        with self.assertRaises(ValueError):self.device.submit(1501,self.now)
        self.assertEqual(self.device.commands,[])
    def test_shadow_does_not_import_physical_driver_or_transport(self):
        forbidden={'vsrv_driver','vsrv_transport','batch_transport','pulse_driver'}
        self.assertFalse(forbidden.intersection(sys.modules))
    def test_live_entry_refuses_host_before_attempting_a_connection(self):
        p=subprocess.run([sys.executable,str(HERE/'run_shadow.py'),'--manifest-sha256','unused','--settings','unused',
            '--output','unused','--confirmation','SHADOW_ONLY'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertIn('no connection attempted on host',p.stderr)


if __name__=='__main__':unittest.main()
