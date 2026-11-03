"""Exercise the real nested capture callbacks with synthetic in-memory frames."""
import ast
import gc
import hashlib
import os
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
import weakref

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASELINE=Path(os.environ['AURA_CAPTURE_BASELINE'])
DIAGNOSTIC=Path(os.environ['AURA_DIAGNOSTIC_BASELINE'])
CANDIDATE=ROOT/'candidate/aura/board/vision/ui_camera_service.py'
OLD='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3).copy()'
NEW='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)'


class Buffer:
    def __init__(self,data):self.data=data
    def extract_dup(self,offset,size):return self.data
    def get_size(self):return len(self.data)


class Sink:
    def __init__(self,data,w=640,h=480,eos=False):
        self.buffer=Buffer(data)
        caps=SimpleNamespace(get_structure=lambda _:SimpleNamespace(get_value=lambda key:{'width':w,'height':h}[key]))
        self.item=None if eos else SimpleNamespace(get_buffer=lambda:self.buffer,get_caps=lambda:caps)
    def emit(self,name):
        assert name=='pull-sample'
        return self.item


def callback(source,*,cv=cv2,identity=True):
    tree=ast.parse(source)
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='sample')
    module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    offered=[];metrics=[]
    state=SimpleNamespace(identity=SimpleNamespace(face_targets=SimpleNamespace(offer=lambda *values:offered.append(values))) if identity else None,
        camera_error='',pipeline_metrics=SimpleNamespace(elapsed=lambda *values:metrics.append(values)))
    captured=[]
    def capture(stamp):captured.append(stamp);return len(captured)
    state.captured=capture
    latest=[None];stop=threading.Event()
    namespace={'np':np,'cv2':cv,'Gst':SimpleNamespace(FlowReturn=SimpleNamespace(OK=0,EOS=1,ERROR=-1)),
        'millis':lambda:123456,'state':state,'condition':threading.Condition(),'latest':latest,'stop':stop,
        'time':__import__('time')}
    exec(compile(module,'<actual capture callback>','exec'),namespace)
    return SimpleNamespace(call=namespace['sample'],state=state,latest=latest,stop=stop,
                           captured=captured,offered=offered,metrics=metrics)


class CaptureCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=BASELINE.read_text()
        cls.candidate=CANDIDATE.read_text()
        cls.diagnostic=DIAGNOSTIC.read_text()
        cls.pixels=((np.arange(640*480*3,dtype=np.uint32)*17+13)%256).astype(np.uint8).reshape(480,640,3)

    def test_exactly_one_copy_removed_from_pinned_production_baseline(self):
        self.assertEqual(hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            '890fea726de2c6d29581ab2ee4c36db5e36df52f3e84ee20cd634fc8961ec2ce')
        self.assertEqual(self.original.count(OLD),1)
        self.assertEqual(self.candidate,self.original.replace(OLD,NEW,1))

    def test_all_pixels_equal_and_input_view_readonly_before_real_flip(self):
        seen=[]
        def flip(image,axis):
            seen.append((image.flags.writeable,axis))
            return cv2.flip(image,axis)
        original=callback(self.original)
        candidate=callback(self.candidate,cv=SimpleNamespace(flip=flip))
        raw=self.pixels.tobytes()
        self.assertEqual(original.call(Sink(raw)),0)
        self.assertEqual(candidate.call(Sink(raw)),0)
        np.testing.assert_array_equal(candidate.latest[0][2],original.latest[0][2])
        np.testing.assert_array_equal(candidate.latest[0][2],self.pixels[:,::-1,:])
        self.assertEqual(seen,[(False,1)])
        self.assertTrue(candidate.latest[0][2].flags.c_contiguous)

    def test_flipped_result_does_not_share_input_memory(self):
        candidate=callback(self.candidate)
        raw=bytearray(self.pixels.tobytes())
        candidate.call(Sink(raw))
        source=candidate.latest[0][2]
        self.assertFalse(np.shares_memory(source,np.frombuffer(raw,np.uint8)))
        self.assertTrue(source.flags.owndata)

    def test_result_survives_release_of_original_data_and_image_references(self):
        image_reference=[]
        def flip(image,axis):
            image_reference.append(weakref.ref(image))
            return cv2.flip(image,axis)
        candidate=callback(self.candidate,cv=SimpleNamespace(flip=flip),identity=False)
        raw=self.pixels.tobytes();sink=Sink(raw)
        candidate.call(sink)
        del raw,sink
        gc.collect()
        self.assertIsNone(image_reference[0]())
        np.testing.assert_array_equal(candidate.latest[0][2],self.pixels[:,::-1,:])

    def test_later_mutation_of_input_cannot_change_published_source(self):
        candidate=callback(self.candidate)
        raw=bytearray(self.pixels.tobytes())
        candidate.call(Sink(raw))
        expected=candidate.latest[0][2].copy()
        raw[:]=b'\x00'*len(raw)
        np.testing.assert_array_equal(candidate.latest[0][2],expected)

    def test_layout_constraints_and_error_flow_unchanged(self):
        for data,w,h in ((b'\x00'*(640*480*3-1),640,480),
                         (b'\x00'*(640*480*3+1),640,480),
                         (b'\x00'*(640*480*3),480,640),
                         (b'\x00'*(640*480*3),639,480)):
            old=callback(self.original);new=callback(self.candidate)
            self.assertEqual(old.call(Sink(data,w,h)),new.call(Sink(data,w,h)))
            self.assertEqual(new.state.camera_error,'Unexpected BGR capture layout')
            self.assertTrue(new.stop.is_set())
            self.assertEqual(new.captured,[])
            self.assertIsNone(new.latest[0])

    def test_metadata_identity_same_source_and_eos_behavior_preserved(self):
        old=callback(self.original);new=callback(self.candidate)
        raw=self.pixels.tobytes()
        old.call(Sink(raw));new.call(Sink(raw))
        self.assertEqual(old.latest[0][:2],new.latest[0][:2])
        self.assertEqual(new.latest[0][:2],(1,123456))
        self.assertIs(new.offered[0][0],new.latest[0][2])
        self.assertEqual(new.offered[0][1:],(1,123456))
        previous=new.latest[0]
        self.assertEqual(new.call(Sink(raw,eos=True)),1)
        self.assertIs(new.latest[0],previous)
        self.assertFalse(new.stop.is_set())

    def test_diagnostic_patch_is_same_single_change_and_keeps_metrics(self):
        self.assertEqual(hashlib.sha256(DIAGNOSTIC.read_bytes()).hexdigest(),
            'e7771f01e0e47e6aa629be74fca74f30803a6ec9ed1a48b97b71de3cc452260f')
        self.assertEqual(self.diagnostic.count(OLD),1)
        changed=self.diagnostic.replace(OLD,NEW,1)
        before=callback(self.diagnostic);after=callback(changed)
        raw=self.pixels.tobytes()
        self.assertEqual(before.call(Sink(raw)),after.call(Sink(raw)))
        np.testing.assert_array_equal(before.latest[0][2],after.latest[0][2])
        self.assertEqual([row[0] for row in after.metrics],['capture.callback_prepare'])
        self.assertEqual(before.latest[0][:2],after.latest[0][:2])
        import difflib
        expected=''.join(difflib.unified_diff(self.diagnostic.splitlines(keepends=True),changed.splitlines(keepends=True),
                fromfile='a/board/vision/ui_camera_service.py',tofile='b/board/vision/ui_camera_service.py'))
        self.assertEqual((ROOT/'diagnostic.patch').read_text(),expected)


if __name__=='__main__':unittest.main(verbosity=2)
