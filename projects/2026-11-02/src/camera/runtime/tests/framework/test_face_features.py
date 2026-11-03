"""Face-only transport, attribution, model fidelity and real HTTP error handling."""
import copy
import hashlib
import io
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from common.face_features import MODEL_ID,MODEL_SHA,PROTOCOL,checked_meta,checked_png,checked_reply,encode_meta,decode_meta
from board.identity.remote_features import RemoteFaceFeatures


def png(width=112,height=112):
    import struct,zlib
    def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(
        b'IDAT',zlib.compress((b'\0'+b'\x80\x90\xa0'*width)*height))+chunk(b'IEND',b'')

def meta(raw):
    return {'protocol':PROTOCOL,'model_id':MODEL_ID,'request_id':'a'*32,
        'target':{'camera_epoch':'camera','track_id':1,'track_generation':1},'frame_id':4,
        'captured_mono_ms':1000,'sha256':hashlib.sha256(raw).hexdigest()}

class FeatureProtocolTests(unittest.TestCase):
    def test_only_a_face_sized_png_with_matching_digest_and_owner_is_accepted(self):
        raw=png();m=meta(raw);self.assertEqual(decode_meta(encode_meta(m)),m);checked_meta(m,raw)
        for data in (png(640,480),b'not png',raw+b'x'*65536):
            with self.assertRaises(ValueError):checked_png(data)
        with self.assertRaises(ValueError):checked_meta(m,png()+b'changed')
        for change in ({'model_id':'different'},{'frame_id':True},{'frame_id':0},{'captured_mono_ms':-1}):
            with self.assertRaises(ValueError):checked_meta(dict(m,**change))

    def test_late_wrong_owner_frame_model_and_nonfinite_vectors_are_rejected(self):
        m=meta(png());reply={'context':m,'embedding':[1.]*128,'inference_ms':12.,'backend':'WINDOWS_CPU_SFACE_ORT'}
        self.assertEqual(len(checked_reply(reply,m)),128)
        for key,value in (('frame_id',5),('model_id','wrong'),('target',dict(m['target'],track_generation=2))):
            with self.assertRaises(ValueError):checked_reply(dict(reply,context=dict(m,**{key:value})),m)
        for vector in ([0.]*128,[float('nan')]*128,[1.]*127,[True]*128):
            with self.assertRaises(ValueError):checked_reply(dict(reply,embedding=vector),m)

    def test_client_is_restricted_to_configured_lan_endpoint(self):
        config={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
        RemoteFaceFeatures(config)
        for change in ({'host':'example.com'},{'port':80},{'timeout_ms':5000},{'kind':'other'}):
            with self.assertRaises(ValueError):RemoteFaceFeatures(dict(config,**change))

    def test_client_sends_face_png_and_refuses_a_mismatched_response(self):
        raw=png();config={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650};seen=[]
        class Connection:
            def __init__(self,*a,**kw):pass
            def request(self,method,path,body,headers):
                self.context=decode_meta(headers['X-Aura-Face']);seen.append((body,path));self.status=200
            def getresponse(self):return self
            def read(self,_):return json.dumps({'context':dict(self.context,frame_id=999),'embedding':[1.]*128,
                'inference_ms':1,'backend':'WINDOWS_CPU_SFACE_ORT'}).encode()
            def close(self):pass
        with patch('board.identity.remote_features.http.client.HTTPConnection',Connection):
            with self.assertRaises(ValueError):RemoteFaceFeatures(config).feature(raw,meta(raw)['target'],4,1000)
        self.assertEqual(seen,[(raw,'/v1/identity/face-features')])

    def test_diagnostics_retain_score_and_margin_rejection_after_reset(self):
        from board.identity.sampling import EnrollmentSampling
        s=EnrollmentSampling(.85,.1,lambda:1000);s.start(meta(png())['target'],0)
        s.stage='validate';s.candidate={'embedding':(1.,0.)}
        q={'pixels':100.,'eye_distance':30.,'blur':100.,'roll':0.,'yaw':0.}
        s.offer({'target':s.owner,'revision':0,'fid':1,'stamp':1000,'embedding':(.8,.6)},q,.75)
        self.assertEqual(s.metrics['score_rejections'],1);self.assertEqual(s.metrics['margin_rejections'],1)
        s.fail('timeout');s.reset()
        self.assertEqual(s.last_failure['metrics']['recent_validation'][0]['score'],.8)
        self.assertNotIn('embedding',repr(s.last_failure))

class FeatureHTTPTests(unittest.TestCase):
    def test_real_handler_is_independent_of_voice_busy_and_rejects_full_frame(self):
        import http.client
        from types import SimpleNamespace
        from tools.asr_server import AsrServer
        from tools.board_model_host import ModelHandler
        class Features:
            def feature(self,m,raw):
                checked_meta(m,raw)
                return {'context':m,'embedding':[1.]*128,'inference_ms':1.,'backend':'WINDOWS_CPU_SFACE_ORT'}
        lock=threading.Lock();lock.acquire()
        server=AsrServer(('127.0.0.1',0),None,handler=ModelHandler)
        server.models=SimpleNamespace(lock=lock,face_features=Features())
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            for raw,expected in ((png(),200),(png(640,480),400)):
                c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
                m=meta(raw);c.request('POST','/v1/identity/face-features',body=raw,
                    headers={'Content-Type':'image/png','X-Aura-Face':encode_meta(m)})
                r=c.getresponse();value=json.loads(r.read());self.assertEqual(r.status,expected)
                if expected==200:self.assertEqual(len(checked_reply(value,m)),128)
                c.close()
        finally:server.shutdown();server.server_close();worker.join(2);lock.release()

class RealSFaceCPUParityTests(unittest.TestCase):
    def test_pinned_windows_onnx_backend_matches_plain_rgb_tensor(self):
        import numpy as np
        from PIL import Image
        from tools.face_feature_host import FaceFeatureHost
        path=Path(__file__).resolve().parents[2]/'models/vision/sface_2021dec.onnx'
        host=FaceFeatureHost(path);raw=png();m=meta(raw);reply=host.feature(m,raw)
        rgb=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'),dtype=np.float32)
        direct=host.session.run(None,{host.input:np.ascontiguousarray(rgb.transpose(2,0,1)[None])})[0].reshape(-1)
        self.assertTrue(np.allclose(checked_reply(reply,m),direct,rtol=1e-5,atol=1e-5))
        self.assertEqual(host.health()['processed'],1);self.assertFalse(host.health()['gpu_used'])
        with self.assertRaises(ValueError):host.feature(m,png(640,480))

if __name__=='__main__':unittest.main()
