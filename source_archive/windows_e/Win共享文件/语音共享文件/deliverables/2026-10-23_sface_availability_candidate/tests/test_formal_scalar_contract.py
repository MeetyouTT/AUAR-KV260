import bootstrap
from types import SimpleNamespace
import unittest
import cv2
import numpy as np
from board.identity.camera_faces import CameraFaceExtractor
from board.identity.store import IdentityStore
from board.identity.live import IdentityService


class ScalarContractTests(unittest.TestCase):
    def test_dpu_numpy_output_crosses_extractor_store_boundary_as_python_scalars(self):
        e=CameraFaceExtractor.__new__(CameraFaceExtractor)
        e.cv2=cv2;e.config={'minimum_face_pixels':48,'minimum_face_score':.9,'minimum_blur_variance':0}
        e.align_crop=lambda image,face:np.full((112,112,3),127,np.uint8)
        e.shadow=None;e.producer_enabled=False;e.remote=None
        vector=np.ones(128,np.float32)
        e.local_dpu=SimpleNamespace(feature=lambda *args,**kw:vector)
        key={'camera_epoch':'fixture','track_id':1,'track_generation':1}
        face=[10,10,100,100,30,40,70,40,50,60,35,80,65,80,.99]
        values,reason=e.extract(np.zeros((480,640,3),np.uint8),
            {'target_kind':'face','face_target':key,'face':face,'captured_mono_ms':1000},key)
        self.assertEqual(reason,'');self.assertEqual(len(values),128)
        self.assertTrue(all(type(value) is float for value in values))
        store=IdentityStore(':memory:','new-int8-model',128,.5,.1)
        try:
            store.enroll('private-id','private-name',[1.]*128,consent=True)
            self.assertEqual(store.match(values).state,'KNOWN')
        finally:store.close()
        self.assertEqual(vector.dtype,np.float32)

    def test_match_decision_counts_are_actual_store_results_and_ignore_expired_packets(self):
        store=IdentityStore(':memory:','new-int8-model',128,.5,.1)
        key={'camera_epoch':'fixture','track_id':1,'track_generation':1}
        service=IdentityService(store,None,lambda:key,clock=lambda:10000)
        try:
            store.enroll('private-id','private-name',[1.]*128,consent=True)
            extractor=SimpleNamespace(extract=lambda *args:([1.]*128,''))
            service.process((None,1,10000,{},key),extractor)
            self.assertEqual(service.health()['match_diagnostics']['counts']['KNOWN'],1)
            extractor.extract=lambda *args:([1.]*64+[-1.]*64,'')
            service.process((None,2,10000,{},key),extractor)
            health=service.health()['match_diagnostics']
            self.assertEqual(health['counts'],{'KNOWN':1,'UNKNOWN':1,'AMBIGUOUS':0})
            self.assertEqual(health['last_state'],'UNKNOWN')
            service.process((None,3,8000,{},key),extractor)
            self.assertEqual(service.health()['match_diagnostics']['counts'],health['counts'])
        finally:store.close()


if __name__=='__main__':unittest.main()
