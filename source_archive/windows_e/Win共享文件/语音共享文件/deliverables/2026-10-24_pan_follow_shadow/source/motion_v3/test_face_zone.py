import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common.motion_observation import PROTOCOL
from face_edge_control import EdgeConfig,FaceEdgeController
from face_motion import run_session
from face_zone import camera_zone

def packet(fid,center):
    return dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',
      board_boot_id='boot',service_epoch='service',camera_epoch='camera',state='READY',
      source_frame_id=fid,source_mono_ms=1000+fid*100,deadline_mono_ms=1250+fid*100,
      frame_width=640,frame_height=480,mirror_horizontal=True,
      target=dict(track_id=1,track_generation=1,box=[center*640-32,100.,64.,80.],score=.95))

class ZoneTests(unittest.TestCase):
    def setUp(self):self.c=FaceEdgeController('boot',1445);self.fid=0
    def feed(self,center):
        self.fid+=1;p=packet(self.fid,center)
        return self.c.observe(p,p['source_mono_ms']+20,allow_fixture=True)
    def test_selected_line_uses_video_content_not_widget(self):
        z=dict(schema='aura-face-zone-settings-1',board_boot_id='boot',target_kind='face',
          reference='face_center',mirror_horizontal=True,frame_width=640,frame_height=480,
          left_ratio=0.,right_ratio=.7158253629442671,viewport=[8,112,568,300])
        value=camera_zone(z,'boot')
        self.assertAlmostEqual(value['right_ratio'],.8064720153808593)
        self.assertEqual(value['content_rect'],[92,112,400,300])
        for key,value in [('board_boot_id','wrong'),('target_kind','body'),('right_ratio',.95)]:
            with self.assertRaises(ValueError):camera_zone(dict(z,**{key:value}),'boot')
    def test_inside_zone_no_motion_including_large_face_near_line(self):
        for center in [.1,.4,.7,.8,.806]*4:self.feed(center)
        self.assertEqual(self.c.pulse_us,1445);self.assertEqual(self.c.velocity,0)
    def test_crossing_then_return_inside_stops_without_filter_overshoot(self):
        for _ in range(10):self.feed(.9)
        self.assertGreater(self.c.pulse_us,1445)
        position=self.c.position
        r=self.feed(.805)
        self.assertEqual(r['reason'],'SAFE_ZONE_HOLD');self.assertEqual(self.c.position,position)
        self.assertEqual(self.c.velocity,0)
    def test_boundary_noise_requires_two_distinct_outside_frames(self):
        for center in [.8,.81,.8,.81,.8,.81]*3:self.feed(center)
        self.assertEqual(self.c.pulse_us,1445)
    def test_speed_step_and_acceleration_until_hard_limit(self):
        previous=self.c.position;velocity=0
        for _ in range(80):
            r=self.feed(.94)
            self.assertLessEqual(abs(self.c.position-previous),4.00001)
            self.assertLessEqual(abs(self.c.velocity),40)
            if r['reason']!='AT_LIMIT':self.assertLessEqual(abs(self.c.velocity-velocity),12.00001)
            self.assertTrue(1425<=r['pulse_us']<=1505)
            previous,velocity=self.c.position,self.c.velocity
        self.assertEqual(self.c.pulse_us,1505)
    def test_body_duplicate_and_loss_cannot_refresh_or_resume(self):
        for _ in range(6):self.feed(.9)
        before=(self.c.position,self.c.proposals)
        p=packet(self.fid,.9)
        self.c.observe(p,p['source_mono_ms']+80,allow_fixture=True)
        self.assertEqual(before,(self.c.position,self.c.proposals))
        p=packet(self.fid+1,.9);p['target_kind']='body'
        self.c.observe(p,p['source_mono_ms']+20,allow_fixture=True)
        self.assertEqual(self.c.reason,'FACE_SOURCE_REQUIRED')
        self.feed(.9);self.assertEqual(before,(self.c.position,self.c.proposals))
    def test_left_boundary_can_be_configured_and_has_correct_direction(self):
        self.c=FaceEdgeController('boot',1445,config=EdgeConfig(left_ratio=.2,right_ratio=.8))
        for _ in range(8):self.feed(.1)
        self.assertLess(self.c.pulse_us,1445)
    def test_stale_stops_and_cannot_rearm(self):
        for _ in range(6):self.feed(.9)
        p=packet(self.fid,.9)
        self.c.observe(p,p['source_mono_ms']+250,allow_fixture=True)
        self.assertEqual(self.c.reason,'SOURCE_EXPIRED')
        self.feed(.9);self.assertTrue(self.c.stopped)

if __name__=='__main__':unittest.main()
