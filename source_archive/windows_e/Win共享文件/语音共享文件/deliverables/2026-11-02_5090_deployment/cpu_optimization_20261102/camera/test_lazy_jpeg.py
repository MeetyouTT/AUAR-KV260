"""Pure tests of the actual candidate's extracted classes and HTTP handler.

No project import, service, device, model or real media is used. Real OpenCV
equivalence is a separate public-pattern probe for root to run in the CPU lab.
"""
import ast
from collections import OrderedDict
import copy
import gc
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
import types
import unittest
from urllib.parse import parse_qs,urlsplit
import uuid
import weakref

import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE/'baseline/9d714b9bd00e__ui_camera_service.py'
CANDIDATE=HERE/'candidate_v2/ui_camera_service.py'
tree=ast.parse(CANDIDATE.read_text(encoding='utf-8'))
baseline=ast.parse(BASE.read_text(encoding='utf-8'))

class PipelineMetrics:
    def __init__(self,**options):pass
    def snapshot(self):return {'enabled':False}

module=types.ModuleType('board.vision.pipeline_metrics');module.PipelineMetrics=PipelineMetrics
sys.modules['board.vision.pipeline_metrics']=module
calibration=types.ModuleType('board.identity.calibration_http');calibration.wrap_handler=lambda handler,state:handler
sys.modules['board.identity.calibration_http']=calibration
space=dict(threading=threading,copy=copy,OrderedDict=OrderedDict,uuid=uuid,time=time,os=__import__('os'),
    millis=lambda:1000,PROTOCOL='test-ui',ACTIONS=(),TRANSPORT='aura-local-bgr-1',
    BaseHTTPRequestHandler=BaseHTTPRequestHandler,urlsplit=urlsplit,parse_qs=parse_qs,json=json)
nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('_PreviewJpeg','CameraState','handler_for')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(CANDIDATE)+'::<pure-extraction>','exec'),space)
PreviewJpeg=space['_PreviewJpeg'];CameraState=space['CameraState']

def image(value=37):
    result=np.empty((480,640,3),dtype=np.uint8);result[:]=value
    result[::17,::19]=(7,128,244)
    return result

class Encoded:
    def __init__(self,value=b'jpeg',size=None):self.value=value;self.nbytes=len(value) if size is None else size
    def tobytes(self):return self.value

class Codec:
    IMWRITE_JPEG_QUALITY=1
    def __init__(self,mode='ok',gate=None,delay=0):
        self.mode=mode;self.gate=gate;self.delay=delay;self.calls=0;self.active=0;self.max_active=0
        self.lock=threading.Lock();self.started=threading.Event();self.arguments=[]
    def imencode(self,extension,pixels,options):
        with self.lock:
            self.calls+=1;self.active+=1;self.max_active=max(self.max_active,self.active)
            self.arguments.append((extension,list(options),pixels.shape,pixels.dtype.name,hashlib.sha256(pixels.tobytes()).hexdigest()))
        self.started.set()
        try:
            if self.gate is not None:
                if not self.gate.wait(2):raise RuntimeError('test encoder gate timeout')
            if self.delay:time.sleep(self.delay)
            if self.mode=='raise':raise RuntimeError('synthetic encoder failure')
            if self.mode=='not_ok':return False,Encoded()
            if self.mode=='oversize':return True,Encoded(size=256*1024+1)
            body=b'jpeg-quality-72:'+hashlib.sha256(pixels.tobytes()).digest()
            return True,Encoded(body)
        finally:
            with self.lock:self.active-=1

def setup_state(codec=None,stamp=950,pixels=None):
    now=[1000]
    state=CameraState('test-boot',epoch='test-service',clock=lambda:now[0])
    state.captured(stamp)
    codec=codec or Codec()
    frame=PreviewJpeg(image() if pixels is None else pixels,codec,state._preview_encode_lock)
    state.publish_preview(1,stamp,frame)
    return state,frame,codec,now

class LazyJpegTests(unittest.TestCase):
    def test_no_codec_work_without_http_request(self):
        state,frame,codec,_=setup_state()
        state.snapshot();state.health()
        self.assertEqual(codec.calls,0)
        self.assertEqual(state.preview_frames,1)
        self.assertEqual(state.health()['preview_jpeg_mode'],'on_request_cache')

    def test_same_painted_image_codec_options_and_identical_bytes(self):
        pixels=image();pixels[4:9,4:9]=(40,220,60)
        original=Codec();ok,expected=original.imencode('.jpg',pixels,[original.IMWRITE_JPEG_QUALITY,72])
        state,_,codec,_=setup_state(pixels=pixels)
        self.assertEqual(state.preview(state.camera_epoch,1),expected.tobytes())
        self.assertEqual(codec.arguments,original.arguments)
        self.assertTrue(ok)

    def test_capture_source_independence(self):
        source=image();painted=source.copy();state,_,_,_=setup_state(pixels=painted)
        expected=hashlib.sha256(painted.tobytes()).hexdigest()
        source[:]=255
        state.preview(state.camera_epoch,1)
        self.assertEqual(state.frames[1][1]._cv2.arguments[0][-1],expected)

    def test_cached_request_encodes_once(self):
        state,frame,codec,_=setup_state()
        first=state.preview(state.camera_epoch,1)
        self.assertEqual(state.preview(state.camera_epoch,1),first)
        self.assertEqual(codec.calls,1);self.assertIsNone(frame._image)
        self.assertEqual(state.preview_jpeg_encodes,1);self.assertEqual(state.preview_jpeg_cache_hits,1)

    def test_same_frame_concurrent_requests_share_one_encoding(self):
        state,_,codec,_=setup_state(Codec(delay=.02))
        results=[];barrier=threading.Barrier(16)
        def work():
            barrier.wait();results.append(state.preview(state.camera_epoch,1))
        threads=[threading.Thread(target=work) for _ in range(16)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(2);self.assertFalse(thread.is_alive())
        self.assertEqual(len(results),16);self.assertTrue(all(value==results[0] and value is not None for value in results))
        self.assertEqual(codec.calls,1);self.assertEqual(state.preview_jpeg_encodes,1)
        self.assertEqual(state.preview_jpeg_cache_hits,15)

    def test_distinct_frame_encoders_remain_serialized(self):
        state,_,codec,_=setup_state(Codec(delay=.01))
        for fid in range(2,9):state.publish_preview(fid,950,PreviewJpeg(image(fid),codec,state._preview_encode_lock))
        threads=[threading.Thread(target=lambda fid=fid:state.preview(state.camera_epoch,fid)) for fid in range(1,9)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(2);self.assertFalse(thread.is_alive())
        self.assertEqual(codec.calls,8);self.assertEqual(codec.max_active,1)

    def test_owner_unknown_sequence_and_camera_fault_rejected_before_encode(self):
        state,_,codec,_=setup_state()
        self.assertIsNone(state.preview('wrong-epoch',1));self.assertIsNone(state.preview(state.camera_epoch,2))
        state.camera_error='synthetic capture lost'
        self.assertIsNone(state.preview(state.camera_epoch,1));self.assertEqual(codec.calls,0)

    def test_ttl_999ms_valid_and_1000ms_expired(self):
        state,_,codec,now=setup_state(stamp=1)
        now[0]=1000;self.assertIsNotNone(state.preview(state.camera_epoch,1))
        now[0]=1001;self.assertIsNone(state.preview(state.camera_epoch,1));self.assertEqual(codec.calls,1)

    def test_future_timestamp_rejected_without_encoding(self):
        state,_,codec,_=setup_state(stamp=1001)
        self.assertIsNone(state.preview(state.camera_epoch,1));self.assertEqual(codec.calls,0)

    def test_expiry_during_encode_rechecked(self):
        state,_,codec,now=setup_state()
        encode=codec.imencode
        def expire(*args):
            result=encode(*args);now[0]=1950;return result
        codec.imencode=expire
        self.assertIsNone(state.preview(state.camera_epoch,1));self.assertEqual(codec.calls,1)

    def test_epoch_change_during_encode_rechecked(self):
        state,_,codec,_=setup_state();epoch=state.camera_epoch;encode=codec.imencode
        def replace(*args):
            result=encode(*args);state.camera_epoch='replacement';return result
        codec.imencode=replace
        self.assertIsNone(state.preview(epoch,1))

    def test_eight_frame_bound_and_retired_storage_released(self):
        state,retired,codec,_=setup_state();old_image=weakref.ref(retired._image)
        for fid in range(2,10):state.publish_preview(fid,950,PreviewJpeg(image(fid),codec,state._preview_encode_lock))
        gc.collect();self.assertEqual(list(state.frames),list(range(2,10)))
        self.assertIsNone(old_image());self.assertIsNone(retired._image);self.assertIsNone(retired._jpeg)
        self.assertIsNone(state.preview(state.camera_epoch,1));self.assertEqual(codec.calls,0)
        self.assertLessEqual(sum(value[1]._image.nbytes for value in state.frames.values()),8*640*480*3)

    def test_retirement_does_not_wait_for_active_encoder(self):
        gate=threading.Event();state,retired,codec,_=setup_state(Codec(gate=gate));results=[]
        worker=threading.Thread(target=lambda:results.append(state.preview(state.camera_epoch,1)));worker.start()
        self.assertTrue(codec.started.wait(1));published=threading.Event()
        def publish():
            for fid in range(2,10):state.publish_preview(fid,950,PreviewJpeg(image(fid),codec,state._preview_encode_lock))
            published.set()
        producer=threading.Thread(target=publish);producer.start()
        self.assertTrue(published.wait(1),'shared camera state must stay available while encoding')
        gate.set();producer.join(1);worker.join(1)
        self.assertEqual(results,[None]);self.assertIsNone(retired._image);self.assertIsNone(retired._jpeg)
        self.assertEqual(codec.calls,1)

    def test_encoder_failures_are_sticky_and_never_return_invalid_bytes(self):
        for mode in ('raise','not_ok','oversize'):
            with self.subTest(mode=mode):
                state,frame,codec,_=setup_state(Codec(mode))
                self.assertIsNone(state.preview(state.camera_epoch,1));self.assertIsNone(state.preview(state.camera_epoch,1))
                self.assertEqual(codec.calls,1);self.assertEqual(state.preview_jpeg_failures,1)
                self.assertIsNone(frame._image);self.assertIsNone(frame._jpeg);self.assertTrue(state.preview_error)

    def test_failed_frame_does_not_poison_new_frame_cache(self):
        state,_,bad,_=setup_state(Codec('raise'))
        self.assertIsNone(state.preview(state.camera_epoch,1))
        good=Codec();state.publish_preview(2,950,PreviewJpeg(image(),good,state._preview_encode_lock))
        value=state.preview(state.camera_epoch,2)
        self.assertIsNotNone(value);self.assertFalse(state.preview_error);self.assertEqual(good.calls,1);self.assertEqual(bad.calls,1)

    def test_late_failure_of_evicted_frame_does_not_pollute_new_error_state(self):
        gate=threading.Event();state,_,bad,_=setup_state(Codec('raise',gate=gate))
        worker=threading.Thread(target=lambda:state.preview(state.camera_epoch,1));worker.start();self.assertTrue(bad.started.wait(1))
        for fid in range(2,10):state.publish_preview(fid,950,PreviewJpeg(image(),Codec(),state._preview_encode_lock))
        gate.set();worker.join(1);self.assertFalse(worker.is_alive());self.assertEqual(state.preview_error,'')

    def test_owned_and_contiguous_bgr_requirement(self):
        codec=Codec();lock=threading.Lock()
        for invalid in (image()[:,::-1],np.zeros((480,640,3),dtype=np.float32),np.zeros((240,320,3),dtype=np.uint8)):
            with self.subTest(shape=invalid.shape):
                with self.assertRaises(ValueError):PreviewJpeg(invalid,codec,lock)

    def test_existing_bytes_cache_remains_compatible(self):
        state,_,codec,_=setup_state();state.publish_preview(2,950,b'already-encoded')
        self.assertEqual(state.preview(state.camera_epoch,2),b'already-encoded');self.assertEqual(codec.calls,0)

    def test_http_jpeg_route_content_headers_and_unknown_epoch(self):
        state,_,codec,_=setup_state()
        server=ThreadingHTTPServer(('127.0.0.1',0),space['handler_for'](state))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
            client.request('GET','/v1/ui/preview.jpg?camera_epoch='+state.camera_epoch+'&frame_id=1')
            response=client.getresponse();body=response.read()
            self.assertEqual(response.status,200);self.assertEqual(response.getheader('Content-Type'),'image/jpeg')
            self.assertEqual(response.getheader('Cache-Control'),'no-store');self.assertEqual(response.getheader('X-Aura-Frame-Id'),'1')
            self.assertEqual(body,state.preview(state.camera_epoch,1));client.close()
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
            client.request('GET','/v1/ui/preview.jpg?camera_epoch=wrong&frame_id=1');response=client.getresponse();response.read()
            self.assertEqual(response.status,404);client.close();self.assertEqual(codec.calls,1)
        finally:server.shutdown();server.server_close();thread.join(1)

    def test_capture_inference_handler_shutdown_and_other_top_level_ast_unchanged(self):
        old={node.name:node for node in baseline.body if isinstance(node,(ast.ClassDef,ast.FunctionDef))}
        new={node.name:node for node in tree.body if isinstance(node,(ast.ClassDef,ast.FunctionDef))}
        for name in set(old)-{'CameraState','run'}:self.assertEqual(ast.dump(old[name]),ast.dump(new[name]),name)
        class WithoutPreview(ast.NodeTransformer):
            def visit_FunctionDef(self,node):
                return None if node.name=='preview' else self.generic_visit(node)
        old_run=WithoutPreview().visit(copy.deepcopy(old['run']));new_run=WithoutPreview().visit(copy.deepcopy(new['run']))
        self.assertEqual(ast.dump(old_run),ast.dump(new_run),'only preview worker body may differ in run')

if __name__=='__main__':unittest.main(verbosity=2)
