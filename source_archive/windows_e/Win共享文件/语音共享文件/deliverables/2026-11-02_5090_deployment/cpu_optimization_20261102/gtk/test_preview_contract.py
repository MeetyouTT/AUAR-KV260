"""Exercise the actual original/candidate preview callbacks using a fake Gst backend."""
import ast
from collections import deque
import copy
import io
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
PIXELS=640*480*3

class Clock:
    value=10.0
    def monotonic(self):return self.value

class Buffer:
    def __init__(self,size):self.data=bytearray(size);self.offset=0;self.pts=0
    @staticmethod
    def new_allocate(_allocator,size,_params):return Buffer(size)
    def fill(self,start,pixels):self.data[start:start+len(pixels)]=pixels
    def memset(self,start,value,size):self.data[start:start+size]=bytes([value])*size

class Pad:
    def add_probe(self,kind,callback):self.callback=callback;return 1
    def remove_probe(self,token):self.removed=token
    def allow(self,buffer):return self.callback(None,SimpleNamespace(get_buffer=lambda:buffer))==1

class Element:
    def __init__(self):self.level=0;self.buffers=[];self.pad=Pad();self.callback=None
    def get_property(self,name):assert name=='current-level-bytes';return self.level
    def emit(self,signal,buffer):assert signal=='push-buffer';self.buffers.append(buffer);return 0
    def connect(self,name,callback):assert name=='handoff';self.callback=callback;return 1
    def disconnect(self,token):self.disconnected=token
    def get_static_pad(self,name):assert name=='sink';return self.pad
    def handoff(self,buffer):self.callback(self,buffer)

class Pipeline:
    def __init__(self,description,fail=False):
        self.description=description;self.fail=fail;self.states=[]
        self.elements={name:Element() for name in ('input','screen','count')}
    def get_by_name(self,name):return self.elements[name]
    def set_state(self,state):
        self.states.append(state)
        return -1 if self.fail and state=='PLAYING' else 0

class Gst:
    MSECOND=1000000
    Buffer=Buffer
    State=SimpleNamespace(PLAYING='PLAYING',NULL='NULL')
    StateChangeReturn=SimpleNamespace(FAILURE=-1)
    FlowReturn=SimpleNamespace(OK=0)
    PadProbeReturn=SimpleNamespace(DROP=0,OK=1)
    PadProbeType=SimpleNamespace(BUFFER=1)
    def __init__(self):self.pipelines=[];self.fail_next=False
    def parse_launch(self,description):
        pipeline=Pipeline(description,self.fail_next);self.fail_next=False;self.pipelines.append(pipeline);return pipeline

class VideoOverlay:
    @staticmethod
    def set_window_handle(screen,handle):screen.handle=handle

def make_worker(version):
    path=HERE/version/'tools/board_camera_preview.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='CameraPreviewWorker')
    clock=Clock()
    space={'deque':deque,'copy':copy,'io':io,'threading':threading,'time':clock,'PIXELS':PIXELS}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),str(path),'exec'),space)
    klass=space['CameraPreviewWorker'];worker=klass.__new__(klass)
    worker.Gst=Gst();worker.GstVideo=SimpleNamespace(VideoOverlay=VideoOverlay)
    worker.lock=threading.RLock();worker.outputs={};worker.reader_owner={'owner':True}
    worker.reader=None;worker.last_key=None;worker.error=''
    return worker,clock

def header(frame=1,stamp=9990,epoch='camera-a'):
    return {'board_boot_id':'boot','service_epoch':'service','camera_epoch':epoch,'frame_id':frame,'captured_mono_ms':stamp}

def display(worker,name='vision'):
    output=worker.outputs[name];source=output['source'];buffer=source.buffers[-1]
    if output['sink_pad'].allow(buffer):output['counter'].handoff(buffer)
    return buffer

class PreviewContract(unittest.TestCase):
    def versions(self):return ('original','candidate')

    def test_only_pipeline_order_changes(self):
        a=(HERE/'original/tools/board_camera_preview.py').read_bytes()
        b=(HERE/'candidate/tools/board_camera_preview.py').read_bytes()
        self.assertEqual(b.replace(b'videoscale ! videoconvert ! video/x-raw,width=',b'videoconvert ! videoscale ! video/x-raw,width='),a)
        ta=ast.parse(a.decode());tb=ast.parse(b.decode())
        for tree in (ta,tb):
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str):
                    node.value=node.value.replace('videoscale ! videoconvert !','videoconvert ! videoscale !')
        self.assertEqual(ast.dump(ta),ast.dump(tb))

    def test_frame_bytes_sequence_and_timestamp_survive(self):
        pixels=bytes((23,89,191))*(640*480)
        for version in self.versions():
            with self.subTest(version=version):
                worker,clock=make_worker(version);worker.attach('vision',42,568,300)
                worker.push(header(),pixels);buffer=display(worker)
                self.assertEqual(buffer.data,pixels)
                self.assertEqual((buffer.offset,buffer.pts),(1,9990*Gst.MSECOND))
                self.assertEqual(worker.outputs['vision']['reference'],{'camera_epoch':'camera-a','frame_id':1,'captured_mono_ms':9990})
                self.assertTrue(worker.read('vision')['frame_visible'])

    def test_exact_stale_and_future_boundaries(self):
        for version in self.versions():
            for stamp,allowed in ((9751,True),(9750,False),(10100,True),(10101,False)):
                with self.subTest(version=version,stamp=stamp):
                    worker,clock=make_worker(version);worker.attach('vision',42,568,300)
                    worker.push(header(stamp=stamp),bytes(PIXELS))
                    output=worker.outputs['vision'];buffer=output['source'].buffers[-1]
                    self.assertEqual(output['sink_pad'].allow(buffer),allowed)

    def test_clear_invalidates_reference_and_pushes_blank_once(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,_=make_worker(version);worker.attach('vision',42,568,300)
                worker.push(header(),b'\xff'*PIXELS);display(worker)
                worker.clear();blank=display(worker)
                self.assertEqual(blank.offset,0);self.assertEqual(blank.data,bytes(PIXELS))
                self.assertFalse(worker.read('vision')['frame_visible'])
                self.assertEqual(worker.outputs['vision']['count'],1)
                count=len(worker.outputs['vision']['source'].buffers);worker.clear()
                self.assertEqual(len(worker.outputs['vision']['source'].buffers),count)

    def test_queue_backpressure_does_not_accumulate(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,_=make_worker(version);worker.attach('vision',42,568,300)
                worker.push(header(),bytes(PIXELS));output=worker.outputs['vision']
                output['source'].level=PIXELS
                worker.push(header(frame=2,stamp=9995),bytes(PIXELS))
                self.assertEqual(len(output['source'].buffers),1)
                self.assertEqual(len(output['frames']),1)

    def test_owner_change_flushes_old_frame_reference(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,_=make_worker(version);worker.attach('vision',42,568,300)
                worker.push(header(),bytes(PIXELS));old=display(worker)
                worker.push(header(frame=2,stamp=9995,epoch='camera-b'),bytes(PIXELS))
                output=worker.outputs['vision']
                self.assertIsNone(output['reference'])
                self.assertIn('NULL',output['pipeline'].states)
                output['counter'].handoff(old)
                self.assertIsNone(output['reference'])
                display(worker)
                self.assertEqual(output['reference']['camera_epoch'],'camera-b')

    def test_detach_and_rebind_reject_old_callbacks(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,_=make_worker(version);worker.attach('vision',42,568,300)
                worker.push(header(),bytes(PIXELS));old=worker.outputs['vision'];buffer=old['source'].buffers[-1]
                worker.detach('vision');worker.attach('vision',43,568,300)
                old['counter'].handoff(buffer)
                self.assertIsNone(worker.outputs['vision']['reference'])
                self.assertFalse(old['sink_pad'].allow(buffer))
                self.assertEqual(old['pipeline'].states[-1],'NULL')

    def test_two_views_keep_independent_lifetimes(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,_=make_worker(version);worker.attach('vision',42,568,300);worker.attach('large',43,587,440)
                worker.push(header(),bytes(PIXELS));display(worker);display(worker,'large')
                self.assertEqual(worker.read('large')['displayed_frames'],1)
                worker.detach('vision')
                self.assertEqual(worker.read('large')['active_outputs'],['large'])
                self.assertTrue(worker.read('large')['frame_visible'])

    def test_read_reference_deadline_is_unchanged(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,clock=make_worker(version);worker.attach('vision',42,568,300)
                worker.push(header(stamp=9990),bytes(PIXELS));display(worker)
                clock.value=10.489;self.assertTrue(worker.read('vision')['frame_visible'])
                clock.value=10.490;self.assertFalse(worker.read('vision')['frame_visible'])
                worker.reader_owner=None
                clock.value=11.489;self.assertTrue(worker.read('vision')['frame_visible'])
                clock.value=11.490;self.assertFalse(worker.read('vision')['frame_visible'])

    def test_failed_start_detaches_pipeline(self):
        for version in self.versions():
            with self.subTest(version=version):
                worker,_=make_worker(version);worker.Gst.fail_next=True
                with self.assertRaises(RuntimeError):worker.attach('vision',42,568,300)
                self.assertFalse(worker.outputs)
                self.assertEqual(worker.Gst.pipelines[-1].states[-1],'NULL')

if __name__=='__main__':
    log=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(PreviewContract)
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (HERE/'UNIT_TEST_RESULTS.txt').write_text(log.getvalue(),encoding='utf-8')
    report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'passed':result.wasSuccessful(),'original_and_candidate_exercised':True,
        'GStreamer_devices_or_services_opened':False,'pixel_resampling_comparison':'Requires root-scheduled gst_synthetic_compare.py on the installed Gst 1.18.5 runtime.'}
    (HERE/'UNIT_TEST_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
