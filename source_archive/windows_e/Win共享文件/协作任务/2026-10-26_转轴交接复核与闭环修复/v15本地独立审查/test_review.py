"""Offline review checks. No model, board, network, service or MMIO access."""
import json,sys,threading,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'face_source_v15_candidate'))
sys.path.insert(1,'/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
import stage_timing
import test_stage_timing as stage_fixtures
import test_face_source_v11 as source_fixtures
from face_observation import observation
from board.vision.dpu_vision_runtime import encode
import cv2
import numpy as np


class ReviewTests(unittest.TestCase):
    def test_other_thread_cannot_enter_the_current_process_ledger(self):
        Service,Adapter,components=stage_fixtures.fixtures()
        original=components['cv'].resize;started=threading.Event();finish=threading.Event()
        def controlled_resize(x,*args):
            if threading.current_thread().name=='review-process':
                started.set();self.assertTrue(finish.wait(.5))
            return original(x,*args)
        components['cv'].resize=controlled_resize
        stage_timing.install(Service,components=components)
        s=Service(None,lambda *a:None,'camera');d=Adapter()
        worker=threading.Thread(name='review-process',target=lambda:s.process(('source',17,1000),d))
        worker.start();self.assertTrue(started.wait(.5))
        try:
            for _ in range(30):components['cv'].resize('unrelated',(320,320))
        finally:finish.set();worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(s._edge_latest_stage_timing['stages']['compat_resize']['calls'],1)
        self.assertIsNone(getattr(stage_timing._local,'record',None))

    def test_observer_data_has_no_images_and_fits_wire_bound(self):
        Service,Adapter,components=stage_fixtures.fixtures()
        stage_timing.install(Service,components=components)
        s=Service(None,lambda *a:None,'camera');s.process(('image-marker',2**53-1,2**53-1),Adapter())
        record=s._edge_latest_stage_timing
        self.assertNotIn('image-marker',json.dumps(record))
        # Give every timing/count a long number, retaining the fixed key set.
        for value in record['stages'].values():
            value.update(calls=999999999,wall_ms=123456789.123,thread_cpu_ms=123456789.123)
        f=source_fixtures.SourceTests();f.setUp();f.frame(1,1000)
        f.face._edge_latest_stage_timing=record
        f.face._edge_latest_detector_timing=dict(frame_id=2**53-1,source_mono_ms=2**53-1,
            process_begin_mono_ns=1234567890123456789,process_return_mono_ns=1234567890123456789,
            native={k:1234567890123456789 for k in
                ('start_ns','native_return_ns','release_decision_ns','after_unlock_ns')})
        f.state.epoch='s'*96;f.state.camera_epoch='c'*96;f.state.boot='b'*36
        payload=observation(f.state)
        payload['face_tracking']['result_reasons']={k:99999999999 for k in
            ('DETECTOR_EXPIRED','FACE_CONTINUITY_LOST','FACE_MEASUREMENT_REJECTED','FACE_ANCHOR_EXPIRED',
             'CURRENT_IMAGE_EXPIRED','NO_FACE_ANCHOR','MISSING_ANCHOR_FRAME','MULTIPLE_FACES','FACE_ERROR')}
        raw=(json.dumps(payload,separators=(',',':'))+'\n').encode()
        self.assertLess(len(raw),8192)
        self.payload_bytes=len(raw)

    def test_later_process_does_not_mutate_an_already_published_record(self):
        Service,Adapter,components=stage_fixtures.fixtures()
        stage_timing.install(Service,components=components)
        s=Service(None,lambda *a:None,'camera');d=Adapter()
        s.process(('image',1,1000),d);old=s._edge_latest_stage_timing;saved=json.dumps(old,sort_keys=True)
        s.process(('image',2,1100),d)
        self.assertEqual(saved,json.dumps(old,sort_keys=True))
        self.assertIsNot(old,s._edge_latest_stage_timing)

    def test_identity_callback_exception_preserves_original_exception(self):
        Service,Adapter,components=stage_fixtures.fixtures()
        stage_timing.install(Service,components=components)
        def failed(*args):raise LookupError('callback-failure')
        s=Service(None,failed,'camera')
        with self.assertRaisesRegex(LookupError,'callback-failure'):s.process(('image',3,1000),Adapter())
        self.assertEqual(s._edge_latest_stage_timing['stages']['identity_callback']['calls'],1)
        self.assertIsNone(getattr(stage_timing._local,'record',None))

    def test_all_256_uint8_levels_match_original_float_quantization(self):
        pixels=np.arange(256,dtype=np.uint8)
        reference=encode(pixels.astype(np.float32)/256.,7)
        integer=np.minimum((pixels.astype(np.uint16)+1)//2,127).astype(np.int8)
        self.assertTrue(np.array_equal(reference,integer))
        unsafe=np.minimum((pixels+np.uint8(1))//2,127).astype(np.int8)
        self.assertNotEqual(int(unsafe[-1]),int(reference[-1]))

    def test_random_bgr_resize_layout_and_saturation_are_bit_equivalent(self):
        rng=np.random.RandomState(733)
        images=[rng.randint(0,256,(480,640,3),dtype=np.uint8),
                np.full((320,320,3),255,np.uint8),np.zeros((320,320,3),np.uint8),
                rng.randint(0,256,(960,1280,3),dtype=np.uint8)[::2,::2]]
        for image in images:
            resized=cv2.resize(image,(320,320),interpolation=cv2.INTER_LINEAR)
            nchw=cv2.dnn.blobFromImage(resized)
            normalized=np.ascontiguousarray(nchw.transpose(0,2,3,1)/256.)
            reference=encode(normalized,7)
            integer=np.ascontiguousarray(np.minimum((resized.astype(np.uint16)+1)//2,127).astype(np.int8)[None])
            self.assertEqual(reference.shape,(1,320,320,3))
            self.assertTrue(np.array_equal(reference,integer))
            self.assertEqual(reference.tobytes(),integer.tobytes())


if __name__=='__main__':unittest.main()
