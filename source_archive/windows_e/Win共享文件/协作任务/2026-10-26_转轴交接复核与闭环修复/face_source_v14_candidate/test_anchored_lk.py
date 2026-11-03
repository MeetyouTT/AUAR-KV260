import importlib.util,json,sys,threading,time,unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(1,'/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
from face_flow import FaceFlow
from face_observation import observation
import test_face_source_v11 as source_tests


class AnchoredLKTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('frozen_v12_flow',
            str(Path(__file__).parent.parent/'face_source_v12/face_flow.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.baseline=module.FaceFlow
        self.gray=np.zeros((240,320),np.uint8)
        patch=np.random.RandomState(44).randint(0,256,(90,90),dtype=np.uint8)
        self.gray[60:150,100:190]=cv2.GaussianBlur(patch,(3,3),0)
        self.box=[100.,60.,90.,90.]
        self.state=FaceFlow.seed(self.gray,self.box)

    def transformed(self,degrees,scale,dx=7,dy=4):
        m=cv2.getRotationMatrix2D((145,105),degrees,scale);m[:,2]+=[dx,dy]
        return cv2.warpAffine(self.gray,m,(320,240)),m

    def test_scale_and_rotation_have_current_pixel_evidence_when_fixed_ncc_rejects(self):
        for degrees,scale in [(6,1.08),(10,1.12),(8,.92),(0,1.12),(-8,1.08)]:
            current,m=self.transformed(degrees,scale)
            baseline=self.baseline.step(None,current,self.baseline.seed(self.gray,self.box),self.box)
            self.assertIsNone(baseline)
            result=FaceFlow.step(None,current,self.state,self.box)
            self.assertIsNotNone(result,(degrees,scale))
            box,state=result
            self.assertEqual(state['method'],'FACE_FIXED_ANCHOR_LK_AFFINE')
            center=np.array([145.,105.])@m[:,:2].T+m[:,2]
            self.assertAlmostEqual(box[0]+box[2]/2,center[0],delta=1.)
            self.assertAlmostEqual(box[1]+box[3]/2,center[1],delta=1.)
            self.assertGreaterEqual(state['match_score'],.80)
            self.assertGreaterEqual(state['lk_inliers'],12)
            self.assertIs(state['template'],self.state['template'])
            self.assertIs(state['anchor_gray'],self.state['anchor_gray'])

    def test_repeated_motion_never_rolls_template_or_anchor_pixels(self):
        box,state=self.box,self.state
        for degrees,scale,dx in [(6,1.08,7),(8,1.10,10),(4,1.06,15),(0,1.,20)]:
            current,_=self.transformed(degrees,scale,dx=dx)
            result=FaceFlow.step(None,current,state,box)
            self.assertIsNotNone(result)
            box,state=result
            self.assertIs(state['anchor_gray'],self.state['anchor_gray'])
            self.assertIs(state['anchor_points'],self.state['anchor_points'])
            self.assertIs(state['template'],self.state['template'])
        self.assertAlmostEqual(box[0],120,delta=1.)

    def test_missing_random_occluded_and_unbounded_transform_are_rejected(self):
        current,_=self.transformed(8,1.10)
        occluded=current.copy();occluded[60:155,140:200]=0
        same_texture_far,_=self.transformed(5,1.05,dx=90)
        extreme,_=self.transformed(25,1.3)
        for image in (np.zeros_like(current),np.random.RandomState(4).randint(0,256,current.shape,dtype=np.uint8),
                      occluded,same_texture_far,extreme):
            self.assertIsNone(FaceFlow.step(None,image,self.state,self.box))

    def test_one_eye_region_cannot_supply_whole_face_transform(self):
        state=dict(self.state);points=FaceFlow.anchor_features(state)
        state['anchor_points']=points.copy()
        state['anchor_points'][:]=np.array([[[125.,85.]]],np.float32)
        current,_=self.transformed(5,1.08)
        self.assertIsNone(FaceFlow.anchored_lk(current,state,self.box))

    def test_lk_result_keeps_original_real_anchor_deadline(self):
        f=source_tests.SourceTests();f.setUp();f.gray=self.gray
        f.frame(1,1000)
        current,_=self.transformed(6,1.08)
        f.detect(2,1200,count=0)
        value=f.frame(3,1350,current)
        self.assertIsNotNone(value)
        self.assertEqual(f.flow.reason,'FACE_FIXED_ANCHOR_LK_AFFINE')
        self.assertEqual(value['anchor_stamp'],1000)
        self.assertEqual(value['stamp'],1350)
        self.assertEqual(observation(f.state)['state'],'READY')
        f.now=1500;f.state.capture_stamp=1499
        self.assertEqual(observation(f.state)['state'],'EXPIRED')
        self.assertIsNone(f.frame(4,1500,current))

    def test_worker_diagnostics_count_unique_sources_rejections_and_gap(self):
        f=source_tests.SourceTests();f.setUp();f.face._edge_signal=threading.Condition();f.face._edge_revision=0
        flow=FaceFlow(f.face)
        try:
            for fid,stamp,gray in ((1,1000,f.gray),(2,1100,np.zeros_like(f.gray)),(3,1200,f.gray)):
                previous=f.face._edge_revision;f.now=stamp+1
                flow.offer(f.image(gray),fid,stamp)
                with f.face._edge_signal:
                    self.assertTrue(f.face._edge_signal.wait_for(lambda:f.face._edge_revision>previous,timeout=2))
            diagnostics=flow.diagnostics()
            self.assertEqual(diagnostics['algorithm_version'],14)
            self.assertEqual(diagnostics['valid_measurements'],1)
            self.assertEqual(diagnostics['result_reasons']['FACE_MEASUREMENT_REJECTED'],1)
            self.assertEqual(diagnostics['result_reasons']['NO_FACE_ANCHOR'],1)
            self.assertEqual(diagnostics['anchor_refreshes'],1)
            self.assertLess(len(json.dumps(diagnostics)),6000)
        finally:flow.close()
