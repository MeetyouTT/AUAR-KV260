import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from face_zone import camera_zone


class ZoneTests(unittest.TestCase):
    def settings(self):
        return dict(schema='aura-face-zone-settings-1',board_boot_id='boot',target_kind='face',reference='face_center',
            mirror_horizontal=True,frame_width=640,frame_height=480,left_ratio=0.,viewport=[8,112,568,300],right_ratio=.7158253629442671)
    def test_authorized_left_line_is_ten_percent_of_camera_not_widget(self):
        p=self.settings();old=camera_zone(p,'boot');p['left_camera_ratio']=.1;new=camera_zone(p,'boot')
        self.assertEqual(new['left_ratio'],.1);self.assertEqual(new['screen_left_line_x'],132.)
        self.assertEqual(new['right_ratio'],old['right_ratio']);self.assertEqual(new['screen_line_x'],old['screen_line_x'])
    def test_legacy_and_invalid_context_boundaries_are_not_misread(self):
        self.assertEqual(camera_zone(self.settings(),'boot')['left_ratio'],0.)
        for value in [-.1,.4,True,float('nan'),'0.1']:
            p=self.settings();p['left_camera_ratio']=value
            with self.assertRaises(ValueError):camera_zone(p,'boot')
        with self.assertRaises(ValueError):camera_zone(self.settings(),'other')


if __name__=='__main__':unittest.main()
