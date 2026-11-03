import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import cv2,numpy as np
sys.path.insert(1,'/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
from board.vision.dpu_vision_runtime import encode,SlotUnavailable
from fast_yunet_input import FastYuNetNetwork,encode_blob_integer_nhwc,install


def adapter_class():
    class Adapter:
        def __init__(self,native=True,fix=7,dims=None):
            self.native_critical=native
            self.runner=SimpleNamespace(input_fix=fix,inputs=[SimpleNamespace(dims=dims or [1,320,320,3])])
            self.detector=SimpleNamespace(net=object());self.original=self.detector.net
            self.fallback=SimpleNamespace(net=object());self.calls=[];self.result=object()
            self._admission_check=lambda:None
            self._admission_check.source_expires_monotonic_ns=123456789
        def _native_scheduled(self,source,guard):
            self.calls.append((source,guard));guard();return self.result
    return Adapter


class FastInputTests(unittest.TestCase):
    def blob(self):return np.arange(256,dtype=np.float32).repeat(1200).reshape(1,3,320,320)
    def test_all256_values_and_layout_match_original(self):
        blob=self.blob();reference=encode(np.ascontiguousarray(blob.transpose(0,2,3,1)/256.),7)
        result=encode_blob_integer_nhwc(blob)
        self.assertEqual(result.tobytes(),reference.tobytes());self.assertTrue(result.flags.c_contiguous)
        self.assertEqual(result.dtype,np.int8);self.assertEqual(result.shape,(1,320,320,3))
        self.assertEqual(int(result.max()),127)
    def test_resize_random_saturation_bgr_and_noncontiguous_sources_match(self):
        rng=np.random.RandomState(733)
        images=[rng.randint(0,256,(480,640,3),dtype=np.uint8),np.full((320,320,3),255,np.uint8),
            np.zeros((320,320,3),np.uint8),rng.randint(0,256,(960,1280,3),dtype=np.uint8)[::2,::2]]
        for image in images:
            blob=cv2.dnn.blobFromImage(cv2.resize(image,(320,320),interpolation=cv2.INTER_LINEAR))
            expected=encode(np.ascontiguousarray(blob.transpose(0,2,3,1)/256.),7)
            self.assertEqual(encode_blob_integer_nhwc(blob).tobytes(),expected.tobytes())
        blob=rng.randint(0,256,(1,3,320,640)).astype(np.float32)[:,:,:,::2]
        self.assertFalse(blob.flags.c_contiguous)
        self.assertEqual(encode_blob_integer_nhwc(blob).tobytes(),encode(np.ascontiguousarray(blob.transpose(0,2,3,1)/256.),7).tobytes())
    def test_invalid_domain_is_rejected_and_old_tensor_cannot_be_reused(self):
        a=adapter_class()();net=FastYuNetNetwork(a,lambda x:x);net.setInput(self.blob())
        invalid=[self.blob().astype(np.float64),np.zeros((1,320,320,3),np.float32)]
        for value in (float('nan'),float('inf'),-1.,256.,.5):
            bad=self.blob();bad.flat[0]=value;invalid.append(bad)
        for blob in invalid:
            with self.assertRaises(ValueError):net.setInput(blob)
            self.assertIsNone(net.source)
            with self.assertRaises(ValueError):net.forward(['loc','conf','iou'])
        self.assertEqual(a.calls,[])
    def test_original_guard_and_transform_are_used_without_changing_deadline(self):
        a=adapter_class()();guard=a._admission_check;names=[];transformed=[]
        def measure(name,f,*args,**kwargs):names.append(name);return f(*args,**kwargs)
        net=FastYuNetNetwork(a,lambda x:transformed.append(x) or 'converted',measure);net.setInput(self.blob())
        self.assertEqual(net.forward(['loc','conf','iou']),'converted')
        self.assertIs(a.calls[0][1],guard);self.assertEqual(guard.source_expires_monotonic_ns,123456789)
        self.assertEqual(transformed,[a.result]);self.assertEqual(names,['fast_input_encode','fast_network_forward'])
    def test_none_wrong_outputs_missing_guard_and_original_error(self):
        a=adapter_class()();net=FastYuNetNetwork(a,lambda x:x);net.setInput(self.blob())
        with self.assertRaises(ValueError):net.forward(['wrong'])
        self.assertEqual(a.calls,[]);a._admission_check=None
        with self.assertRaises(ValueError):net.forward(['loc','conf','iou'])
        a._admission_check=lambda:None;a.result=None
        with self.assertRaises(SlotUnavailable):net.forward(['loc','conf','iou'])
        def failed(*args):raise RuntimeError('original-native-error')
        a._native_scheduled=failed
        with self.assertRaisesRegex(RuntimeError,'original-native-error'):net.forward(['loc','conf','iou'])
    def test_only_reviewed_native_instances_change_and_fallback_is_untouched(self):
        Adapter=adapter_class();install(Adapter,lambda x:x)
        for options in ({'native':False},{'fix':8},{'dims':[1,192,192,3]}):
            a=Adapter(**options);self.assertIs(a.detector.net,a.original)
        a=Adapter();self.assertIsInstance(a.detector.net,FastYuNetNetwork)
        fallback=a.fallback.net;original_init=Adapter.__init__;install(Adapter,lambda x:x)
        self.assertIs(Adapter.__init__,original_init);self.assertIs(a.fallback.net,fallback)


if __name__=='__main__':unittest.main()
