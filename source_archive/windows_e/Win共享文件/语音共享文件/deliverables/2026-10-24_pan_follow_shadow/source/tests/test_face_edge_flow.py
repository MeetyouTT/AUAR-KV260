"""Synthetic image evidence for measured translation and target-loss rejection."""
from pathlib import Path
import sys,threading,time,unittest
from types import SimpleNamespace
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'face_edge_v5'))
from face_flow import FaceFlow


class FlowTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.RandomState(3)
        self.gray=np.zeros((480,640),dtype=np.uint8)
        self.gray[120:240,200:320]=rng.randint(0,256,(120,120),dtype=np.uint8)
        self.box=[200.,120.,120.,120.]
    def test_image_translation_moves_face_box_by_measured_pixels(self):
        points=FaceFlow.seed(self.gray,self.box)
        moved=cv2.warpAffine(self.gray,np.float32([[1,0,8],[0,1,-3]]),(640,480))
        box,tracked=FaceFlow.step(self.gray,moved,points,self.box)
        self.assertAlmostEqual(box[0],208.,delta=.2);self.assertAlmostEqual(box[1],117.,delta=.2)
        self.assertGreaterEqual(len(tracked),10)
    def test_blank_frame_cannot_continue_a_lost_face(self):
        points=FaceFlow.seed(self.gray,self.box)
        self.assertIsNone(FaceFlow.step(self.gray,np.zeros_like(self.gray),points,self.box))
    def test_worker_uses_current_capture_stamp_and_keeps_detection_stamp_separate(self):
        face=SimpleNamespace(lock=threading.RLock(),key=None,stamp=None,tracker=SimpleNamespace(last_frame=None,tracks={}),
            ready=True,error='',fault_latched=False,count=0,ttl=1000,_edge_signal=threading.Condition(),_edge_revision=0)
        flow=FaceFlow(face)
        try:
            image=cv2.cvtColor(self.gray,cv2.COLOR_GRAY2BGR)
            flow.offer(image,1,1000)
            time.sleep(.03)
            with face.lock:
                face.key={'track_id':1,'track_generation':2};face.stamp=1000;face.tracker.last_frame=1;face.count=1
                face.tracker.tracks={1:dict(visible=True,confirmed=True,frame_id=1,box=self.box,score=.95)}
            moved=cv2.warpAffine(image,np.float32([[1,0,8],[0,1,0]]),(640,480))
            flow.offer(moved,2,1100)
            end=time.monotonic()+1
            while flow.snapshot()[0] is None and time.monotonic()<end:time.sleep(.005)
            value,error=flow.snapshot();self.assertEqual(error,'');self.assertIsNotNone(value)
            self.assertEqual(value['stamp'],1100);self.assertEqual(value['anchor_stamp'],1000)
            self.assertAlmostEqual(value['box'][0],208.,delta=.2)
            with face.lock:face.count=0;face.key=None;face.stamp=1200
            flow.offer(moved,3,1200)
            end=time.monotonic()+1
            while flow.snapshot()[0] is not None and time.monotonic()<end:time.sleep(.005)
            self.assertIsNone(flow.snapshot()[0])
        finally:flow.close()


if __name__=='__main__':unittest.main()
