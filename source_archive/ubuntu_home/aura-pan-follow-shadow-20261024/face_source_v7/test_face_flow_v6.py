import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import cv2,numpy as np
from face_flow import FaceFlow

class FlowTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.RandomState(3);self.gray=np.zeros((240,320),np.uint8)
        self.gray[60:150,100:190]=rng.randint(0,256,(90,90),dtype=np.uint8);self.box=[100.,60.,90.,90.]
    def test_translation_is_current_pixel_measurement(self):
        moved=cv2.warpAffine(self.gray,np.float32([[1,0,8],[0,1,-3]]),(320,240))
        box,state=FaceFlow.step(self.gray,moved,FaceFlow.seed(self.gray,self.box),self.box)
        self.assertAlmostEqual(box[0],108.,delta=.5);self.assertAlmostEqual(box[1],57.,delta=.5)
    def test_visible_face_can_touch_and_partially_cross_left_edge(self):
        image=np.zeros_like(self.gray);image[60:150,6:96]=self.gray[60:150,100:190];box=[6.,60.,90.,90.]
        moved=cv2.warpAffine(image,np.float32([[1,0,-12],[0,1,0]]),(320,240))
        result=FaceFlow.step(image,moved,FaceFlow.seed(image,box),box);self.assertIsNotNone(result)
        measured,state=result;self.assertLess(measured[0],0);clipped=FaceFlow.clipped(measured,moved.shape)
        self.assertEqual(clipped[0],0);self.assertGreater(clipped[2],48)
    def test_blank_and_unrelated_texture_are_not_tracked(self):
        seed=FaceFlow.seed(self.gray,self.box)
        self.assertIsNone(FaceFlow.step(self.gray,np.zeros_like(self.gray),seed,self.box))
        other=np.random.RandomState(30).randint(0,256,self.gray.shape,dtype=np.uint8)
        self.assertIsNone(FaceFlow.step(self.gray,other,seed,self.box))
    def test_background_movement_does_not_move_face(self):
        rng=np.random.RandomState(32);background=rng.randint(0,128,self.gray.shape,dtype=np.uint8)
        previous=background.copy();previous[60:150,100:190]=self.gray[60:150,100:190]
        current=cv2.warpAffine(background,np.float32([[1,0,12],[0,1,0]]),(320,240));current[60:150,100:190]=previous[60:150,100:190]
        measured,_=FaceFlow.step(previous,current,FaceFlow.seed(previous,self.box),self.box)
        self.assertAlmostEqual(measured[0],100.,delta=.5)
    def test_mostly_lost_face_is_rejected(self):
        self.assertIsNone(FaceFlow.clipped([-60.,60.,90.,90.],self.gray.shape))

if __name__=='__main__':unittest.main()
