import unittest
from unittest.mock import patch
from pathlib import Path
import cv2
import numpy as np
from face_flow import FaceFlow


class LazyFeatureTests(unittest.TestCase):
    def setUp(self):
        self.gray=np.zeros((240,320),np.uint8)
        self.gray[60:150,100:190]=cv2.GaussianBlur(
            np.random.RandomState(44).randint(0,256,(90,90),dtype=np.uint8),(3,3),0)
        self.box=[100.,60.,90.,90.]

    def transformed(self,degrees=6,scale=1.08,dx=7):
        m=cv2.getRotationMatrix2D((145,105),degrees,scale);m[:,2]+=[dx,4]
        return cv2.warpAffine(self.gray,m,(320,240))

    def test_seed_and_ordinary_translation_never_extract_lk_features(self):
        with patch('cv2.goodFeaturesToTrack',side_effect=AssertionError('eager feature extraction')):
            state=FaceFlow.seed(self.gray,self.box)
            result=FaceFlow.step(None,self.transformed(0,1.),state,self.box)
            self.assertIsNotNone(result)
            self.assertEqual(result[1]['method'],'FACE_TEMPLATE_VISIBLE_CLIP')
            self.assertNotIn('anchor_points',state)

    def test_features_are_extracted_once_from_original_anchor_and_reused(self):
        state=FaceFlow.seed(self.gray,self.box);original=cv2.goodFeaturesToTrack;images=[]
        def tracked(image,*args,**kwargs):images.append(image);return original(image,*args,**kwargs)
        with patch('cv2.goodFeaturesToTrack',side_effect=tracked):
            first=FaceFlow.step(None,self.transformed(),state,self.box)
            self.assertIsNotNone(first);box,new_state=first
            second=FaceFlow.step(None,self.transformed(8,1.10,10),new_state,box)
            self.assertIsNotNone(second)
        self.assertEqual(len(images),1)
        self.assertIs(images[0],state['anchor_gray'])
        self.assertIs(second[1]['anchor_points'],state['anchor_points'])

    def test_failed_feature_extraction_is_cached_without_current_frame_reseeding(self):
        state=FaceFlow.seed(self.gray,self.box)
        with patch('cv2.goodFeaturesToTrack',return_value=None) as detector:
            self.assertIsNone(FaceFlow.anchored_lk(self.transformed(),state,self.box))
            self.assertIsNone(FaceFlow.anchored_lk(self.transformed(8,1.1),state,self.box))
            self.assertEqual(detector.call_count,1)
        self.assertIn('anchor_points',state)
        self.assertIsNone(state['anchor_points'])
