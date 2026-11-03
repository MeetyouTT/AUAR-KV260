import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));sys.path.insert(0,str(Path(__file__).parents[1]))
from continuous_face_control import EdgeConfig,FaceEdgeController
from common.motion_observation import PROTOCOL


def replay(centers,config=None):
    controller=FaceEdgeController('boot',1445,config=config or EdgeConfig());rows=[]
    for fid,center in enumerate(centers,1):
        stamp=1000+fid*50
        p=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',board_boot_id='boot',
          service_epoch='s',camera_epoch='c',state='READY',source_frame_id=fid,source_mono_ms=stamp,
          deadline_mono_ms=stamp+250,frame_width=640,frame_height=480,mirror_horizontal=True,
          target=dict(track_id=1,track_generation=1,box=[center*640-40,100.,80.,80.],score=.95),
          irrelevant_body_box=[fid*7,0,100,300])
        rows.append(controller.observe(p,stamp+20,allow_fixture=True))
    return controller,rows


class FeedbackTests(unittest.TestCase):
    def test_fast_outward_face_receives_more_speed_than_static_face_at_same_final_position(self):
        moving=[.81+i*.004 for i in range(20)]
        a,fast=replay(moving);b,static=replay([moving[-1]]*20)
        self.assertGreater(fast[-1]['face_image_velocity_ratio_s'],.07)
        self.assertGreater(fast[-1]['requested_velocity_us_s'],static[-1]['requested_velocity_us_s']+5)
        self.assertGreater(a.velocity,b.velocity)
    def test_inward_face_slows_before_boundary_and_raw_return_stops_immediately(self):
        moving=[.90-i*.004 for i in range(20)]
        a,slow=replay(moving);b,static=replay([moving[-1]]*20)
        self.assertLess(slow[-1]['face_image_velocity_ratio_s'],-.07)
        self.assertLess(slow[-1]['requested_velocity_us_s'],static[-1]['requested_velocity_us_s']-5)
        c,rows=replay(moving+[.80])
        self.assertEqual(rows[-1]['reason'],'SAFE_ZONE_HOLD');self.assertEqual(c.velocity,0)
        self.assertEqual(rows[-1]['pulse_us'],rows[-2]['pulse_us'])
        self.assertGreater(rows[-1]['median_center_ratio'],c.config.right_ratio)
    def test_median_rejects_single_bad_measurement_during_following(self):
        values=[.85]*10+[.93]+[.85]*12
        a,smooth=replay(values);b,raw=replay(values,EdgeConfig(median_window=1))
        self.assertAlmostEqual(smooth[10]['median_center_ratio'],.85)
        self.assertAlmostEqual(smooth[10]['requested_velocity_us_s'],24)
        self.assertGreater(raw[10]['requested_velocity_us_s'],50)
        variation=lambda r:sum(abs(a['velocity_us_s']-b['velocity_us_s']) for a,b in zip(r[8:],r[9:]))
        self.assertLess(variation(smooth),variation(raw))
    def test_fast_body_or_face_motion_inside_zone_never_changes_pulse(self):
        c,rows=replay([.5+.2*math.sin(i*.7) for i in range(120)])
        self.assertTrue(all(r['pulse_us']==1445 and r['velocity_us_s']==0 for r in rows))
        self.assertEqual(c.proposals,0)
    def test_speed_step_acceleration_and_travel_stay_bounded(self):
        c,rows=replay([.81+i*.004 for i in range(30)])
        last_position=1445;velocity=0.
        for r in rows:
            self.assertLessEqual(abs(r['velocity_us_s']),60)
            self.assertLessEqual(abs(r['step_velocity_us_s']),60.00001)
            self.assertLessEqual(abs(r['pulse_us']-last_position),4)
            if r['reason']!='AT_LIMIT':self.assertLessEqual(abs(r['velocity_us_s']-velocity),6.00001)
            self.assertTrue(1425<=r['pulse_us']<=1505)
            last_position,velocity=r['pulse_us'],r['velocity_us_s']
    def test_configuration_rejects_nonfinite_or_unbounded_feedback(self):
        for change in ({'velocity_gain_us':float('nan')},{'median_window':4},{'maximum_speed_us_s':90},
                       {'face_velocity_clip_ratio_s':0},{'minimum_us':1399}):
            with self.assertRaises(ValueError):EdgeConfig(**change)

if __name__=='__main__':unittest.main()
