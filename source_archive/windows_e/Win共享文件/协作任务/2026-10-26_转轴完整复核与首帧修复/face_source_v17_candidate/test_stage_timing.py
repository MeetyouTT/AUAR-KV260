import json,threading,unittest
from types import SimpleNamespace
import stage_timing


def fixtures():
    cv=SimpleNamespace(resize=lambda x,*a:x,dnn=SimpleNamespace(blobFromImage=lambda x:x,NMSBoxes=lambda *a:[0]))
    adapter_module=SimpleNamespace(encode=lambda x,*a:x)
    runtime_module=SimpleNamespace(yunet_outputs=lambda x:x)
    class Native:
        def execute_encoded(self,source,**kwargs):return source
    class Network:
        def setInput(self,x):self.source=x
        def forward(self,names):return runtime_module.yunet_outputs(self.adapter.scheduled(self.source))
    class Compat:
        def detect(self,image):
            value=cv.resize(image,(320,320));value=cv.dnn.blobFromImage(value)
            self.net.setInput(value);result=self.net.forward(['loc','conf','iou'])
            cv.dnn.NMSBoxes([],[],.9,.3);return result
    class Adapter:
        def __init__(self):
            self.native=Native();self.detector=Compat();self.detector.net=Network();self.detector.net.adapter=self
        def detect(self,x):return self.detector.detect(x)
        def scheduled(self,x):return self._native_scheduled(adapter_module.encode(x,7),None)
        def _native_scheduled(self,x,check):return self.native.execute_encoded(x)
    class Service:
        def __init__(self,factory,callback,camera_epoch,**kwargs):self.lock=threading.RLock();self.callback=callback
        def process(self,packet,detector,**kwargs):
            result=detector.detect(packet[0]);self.callback(result);return result
    components=dict(cv=cv,adapter_module=adapter_module,runtime_module=runtime_module,
        native=Native,network=Network,compat=Compat,adapter=Adapter)
    return Service,Adapter,components


class StageTests(unittest.TestCase):
    def test_original_results_callbacks_and_source_identity_are_preserved(self):
        Service,Adapter,components=fixtures();stage_timing.install(Service,components=components)
        callbacks=[];s=Service(None,callbacks.append,'camera');d=Adapter();image=object()
        self.assertIs(s.process((image,7,1000),d),image);self.assertEqual(callbacks,[image])
        record=s._edge_latest_stage_timing;self.assertEqual(record['frame_id'],7)
        self.assertEqual(record['source_mono_ms'],1000)
        for name in ('encode_int8','compat_resize','compat_blob','compat_nms','layout_normalize',
                     'native_call_with_result_handling','identity_callback','total_process'):
            self.assertEqual(record['stages'][name]['calls'],1)
            self.assertGreaterEqual(record['stages'][name]['wall_ms'],0)
            self.assertGreaterEqual(record['stages'][name]['thread_cpu_ms'],0)
        self.assertLess(len(json.dumps(record)),4000)
        self.assertIsNone(stage_timing._local.record)
    def test_original_error_propagates_and_context_is_released(self):
        Service,Adapter,components=fixtures();stage_timing.install(Service,components=components)
        def failed(*args):raise ValueError('original-error')
        d=Adapter();d.native.execute_encoded=failed;s=Service(None,lambda *a:None,'camera')
        with self.assertRaisesRegex(ValueError,'original-error'):s.process(('x',8,1000),d)
        self.assertIsNone(stage_timing._local.record)
        self.assertEqual(s._edge_latest_stage_timing['frame_id'],8)
    def test_unrelated_threads_and_calls_do_not_enter_the_ledger(self):
        Service,Adapter,components=fixtures();stage_timing.install(Service,components=components)
        d=Adapter();value=object();self.assertIs(d.detect(value),value)
        self.assertIsNone(getattr(stage_timing._local,'record',None))
        before=Service.process;stage_timing.install(Service,components=components)
        self.assertIs(Service.process,before)
