"""Pixel orientation and resulting tracking coordinate sign."""
import unittest
import numpy as np
from realtime_vision import orient_frame
from vision_core import FaceTracks, ControlPreview
class OrientationTests(unittest.TestCase):
    def test_asymmetric_pixels(self):
        raw=np.arange(3*7*3,dtype=np.uint8).reshape(3,7,3)
        before=raw.copy()
        result=orient_frame(raw,True)
        np.testing.assert_array_equal(result,raw[:,::-1,:])
        np.testing.assert_array_equal(raw,before)
        self.assertFalse(np.shares_memory(result,raw))
        self.assertIs(orient_frame(raw),raw)
        np.testing.assert_array_equal(orient_frame(result,True),raw)
    def test_tracking_control_matches_oriented_image(self):
        raw=np.zeros((480,640,3),np.uint8)
        raw[100:180,440:520]=255
        for mirror,direction in [(False,'RIGHT'),(True,'LEFT')]:
            image=orient_frame(raw,mirror)
            yy,xx=np.where(image[:,:,0]==255)
            face=[int(xx.min()),int(yy.min()),int(xx.max()-xx.min()+1),80]+[0.]*10+[.99]
            tracker=FaceTracks('mirror-'+str(mirror),confirm_observations=1)
            snapshot=tracker.update([face],1,1.,640,480)
            result=ControlPreview().update(snapshot,640,1.01)
            self.assertEqual(result['direction'],direction)
            self.assertFalse(result['actuation_authorized'])
            self.assertFalse(result['motion_command_emitted'])
if __name__=='__main__':unittest.main()
