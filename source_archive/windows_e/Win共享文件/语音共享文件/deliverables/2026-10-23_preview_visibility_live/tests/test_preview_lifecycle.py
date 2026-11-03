"""Synthetic GTK/Gst lifecycle checks; no devices, windows or models."""
import ast
from collections import deque
import copy
import importlib.util
from pathlib import Path
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
local_preview=ModuleType('board.vision.local_preview')
local_preview.PIXELS=640*480*3;local_preview.RawFrameReader=Mock()
spec=importlib.util.spec_from_file_location('preview_candidate',ROOT/'candidate/aura/tools/board_camera_preview.py')
module=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'board.vision.local_preview':local_preview}):spec.loader.exec_module(module)


class Buffer:
    def __init__(self,size):self.data=bytearray(size);self.offset=self.pts=0
    @classmethod
    def new_allocate(cls,_,size,__):return cls(size)
    def fill(self,offset,data):self.data[offset:offset+len(data)]=data
    def memset(self,offset,value,size):self.data[offset:offset+size]=bytes([value])*size


class Element:
    def __init__(self,pipeline,name):
        self.pipeline,self.name=pipeline,name;self.handler=self.probe=None
        self.buffers=[];self.flow='OK';self.level=0;self.on_emit=None
        self.disconnected=[];self.removed_probes=[]
    def get_static_pad(self,_):return self
    def add_probe(self,_,callback):self.probe=callback;return 9
    def connect(self,_,callback):self.handler=callback;return 7
    def disconnect(self,handler_id):self.disconnected.append(handler_id);self.handler=None
    def remove_probe(self,probe_id):self.removed_probes.append(probe_id);self.probe=None
    def get_property(self,_):return self.level
    def emit(self,action,buffer):
        assert action=='push-buffer'
        self.buffers.append(buffer)
        if self.on_emit:self.on_emit()
        if self.flow=='OK' and self.pipeline.elements['count'].handler:
            self.pipeline.elements['count'].handler(self,buffer)
        return self.flow


class Pipeline:
    def __init__(self,gst,description):
        self.gst,self.description=gst,description;self.states=[]
        self.elements={name:Element(self,name) for name in ('input','count','screen')}
        self.error=None
    def get_by_name(self,name):return self.elements[name]
    def set_state(self,state):
        # Gst may wait for handoff callbacks; the global callback lock must be free.
        assert not self.gst.worker.lock._is_owned()
        self.states.append(state);return 'SUCCESS'
    def get_bus(self):return self
    def pop_filtered(self,_):return self.error


class Gst:
    MSECOND=1000000
    State=SimpleNamespace(NULL='NULL',PLAYING='PLAYING')
    StateChangeReturn=SimpleNamespace(FAILURE='FAILURE')
    FlowReturn=SimpleNamespace(OK='OK')
    PadProbeReturn=SimpleNamespace(OK='OK',DROP='DROP')
    PadProbeType=SimpleNamespace(BUFFER='BUFFER')
    MessageType=SimpleNamespace(ERROR='ERROR')
    Buffer=Buffer
    def __init__(self,worker):self.worker=worker;self.pipelines=[]
    def parse_launch(self,description):
        pipe=Pipeline(self,description);self.pipelines.append(pipe);return pipe


class StopAfter:
    def __init__(self,iterations):self.iterations=iterations
    def wait(self,_):self.iterations-=1;return self.iterations<0


def worker():
    w=module.CameraPreviewWorker.__new__(module.CameraPreviewWorker)
    w.lock=threading.RLock();w.outputs={};w.error=''
    w.reader=w.reader_owner=w.last_key=None;w.raw_directory='/unused'
    w.Gst=Gst(w);w.GstVideo=SimpleNamespace(VideoOverlay=SimpleNamespace(set_window_handle=Mock()))
    w.services=Mock();return w


def header(fid=7):
    return {'board_boot_id':'boot','service_epoch':'service','camera_epoch':'camera',
            'frame_id':fid,'captured_mono_ms':int(time.monotonic()*1000)}


class WorkerLifecycleTests(unittest.TestCase):
    def test_vision_detach_keeps_independent_large_output_and_original_pixels(self):
        w=worker();w.attach('vision',11,160,120);w.attach('large',22,587,440)
        retired=w.outputs['vision'];large=w.outputs['large'];w.detach('vision')
        h=header();old=copy.deepcopy(h);pixels=bytes(range(128))*3
        w.push(h,pixels)
        self.assertEqual(retired['pipeline'].states[-1],'NULL')
        self.assertEqual(retired['source'].buffers,[])
        self.assertEqual(bytes(large['source'].buffers[-1].data),pixels)
        self.assertEqual(large['source'].buffers[-1].offset,h['frame_id'])
        self.assertEqual(large['source'].buffers[-1].pts,h['captured_mono_ms']*w.Gst.MSECOND)
        self.assertEqual(h,old)
        self.assertFalse(w.read('vision')['sink_active'])
        self.assertTrue(w.read('large')['sink_active'])
        self.assertEqual(w.read('large')['active_outputs'],['large'])

    def test_zero_outputs_never_reads_services_or_raw_frame_and_resets_reader(self):
        w=worker();w.reader=object();w.reader_owner={'old':True};w.last_key={'old':True}
        w.stop=StopAfter(3)
        with patch.object(module,'RawFrameReader') as reader:w.work()
        w.services.read.assert_not_called();reader.assert_not_called()
        self.assertIsNone(w.reader);self.assertIsNone(w.reader_owner);self.assertIsNone(w.last_key)

    def test_reopen_same_epoch_reads_current_frame_again(self):
        w=worker();w.stop=StopAfter(1);w.work()
        w.attach('vision',11,160,120)
        h=header();pixels=b'original-pixels';fake_reader=Mock()
        fake_reader.read.return_value=(h,pixels)
        w.services.read.return_value={'snapshot':{'modules':{'camera':{'state':'READY'}},
            'board_boot_id':'boot','service_epoch':'service','preview':{'camera_epoch':'camera'}},'raw_preview':True}
        w.stop=StopAfter(1)
        with patch.object(module,'RawFrameReader',return_value=fake_reader) as reader:w.work()
        reader.assert_called_once();fake_reader.read.assert_called_once()
        self.assertEqual(bytes(w.outputs['vision']['source'].buffers[-1].data),pixels)

    def test_retired_handoff_and_probe_do_not_publish_reference(self):
        w=worker();w.attach('vision',11,160,120);old=w.outputs['vision'];w.push(header(),b'pixels')
        count=old['count'];ref=dict(old['reference']);callback=old['pipeline'].elements['count']
        handed_off,stale_probe=callback.handler,callback.probe
        buffer=old['source'].buffers[-1];w.detach('vision');w.attach('vision',11,160,120)
        handed_off(callback,buffer)
        result=stale_probe(callback,SimpleNamespace(get_buffer=lambda:buffer))
        self.assertEqual(result,'DROP');self.assertEqual(old['count'],count);self.assertEqual(old['reference'],ref)
        self.assertIsNone(w.outputs['vision']['reference'])

    def test_retire_during_push_ignores_old_flushing_and_detach_cannot_deadlock(self):
        w=worker();w.attach('vision',11,160,120);old=w.outputs['vision'];old['source'].flow='FLUSHING'
        threads=[]
        def retire():
            t=threading.Thread(target=w.detach,args=('vision',),daemon=True);threads.append(t);t.start()
            deadline=time.monotonic()+1
            while w.is_current('vision',old) and time.monotonic()<deadline:time.sleep(.001)
            if w.is_current('vision',old):raise AssertionError('detach could not retire output')
        old['source'].on_emit=retire
        w.push(header(),b'pixels')
        threads[0].join(1)
        self.assertFalse(threads[0].is_alive());self.assertEqual(w.error,'')
        self.assertEqual(old['pipeline'].states[-1],'NULL')

    def test_current_output_flow_error_remains_visible(self):
        w=worker();w.attach('vision',11,160,120);w.outputs['vision']['source'].flow='FLUSHING'
        with self.assertRaisesRegex(RuntimeError,'Native preview buffer was rejected'):w.push(header(),b'pixels')

    def test_owner_rebind_does_not_restart_retired_output(self):
        w=worker();w.attach('vision',11,160,120);old=w.outputs['vision'];old['owner']=('old','old','old')
        original=old['pipeline'].set_state
        def retire_on_null(state):
            result=original(state)
            if state=='NULL':
                with w.lock:w.outputs.pop('vision',None)
            return result
        old['pipeline'].set_state=retire_on_null
        w.push(header(),b'pixels')
        self.assertEqual(old['pipeline'].states,['PLAYING','NULL'])
        self.assertEqual(old['source'].buffers,[])

    def test_detach_is_idempotent_clear_does_not_recreate_output(self):
        w=worker();w.attach('large',22,587,440);old=w.outputs['large']
        w.detach('large');w.detach('large');w.clear()
        self.assertEqual(old['pipeline'].states,['PLAYING','NULL'])
        self.assertEqual(old['counter'].disconnected,[7]);self.assertEqual(old['sink_pad'].removed_probes,[9])
        self.assertEqual(w.outputs,{})


tree=ast.parse((ROOT/'candidate/aura/tools/board_avatar_gtk.py').read_text())
gtk_class=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardAvatarStage')
selected=[n for n in gtk_class.body if isinstance(n,ast.FunctionDef) and n.name in ('attach_preview','detach_preview')]
namespace={}
exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='Stage',bases=[],keywords=[],body=selected,decorator_list=[])],type_ignores=[])),
             'extracted-current-GTK-methods','exec'),namespace)
Stage=namespace['Stage']


class GtkLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.gi=ModuleType('gi');self.gi.require_version=Mock();repo=ModuleType('gi.repository')
        repo.GdkX11=SimpleNamespace(X11Window=SimpleNamespace(get_xid=lambda window:window.xid))
        self.modules=patch.dict(sys.modules,{'gi':self.gi,'gi.repository':repo});self.modules.start();self.addCleanup(self.modules.stop)
        self.stage=Stage();self.stage.preview_output=Mock();self.callbacks=[]
        self.stage.GLib=SimpleNamespace(timeout_add=lambda delay,callback:self.callbacks.append(callback))
        self.stage.Gdk=SimpleNamespace(Display=SimpleNamespace(get_default=lambda:SimpleNamespace(sync=Mock())))
        self.area=Mock();self.area.get_window.return_value=SimpleNamespace(xid=77)
        self.area.get_realized.return_value=self.area.get_mapped.return_value=True

    def test_map_unmap_same_xid_remap_rebinds_and_clears_binding(self):
        s=self.stage;s.attach_preview(self.area,'vision',160,120);self.callbacks.pop(0)()
        self.assertEqual(s.preview_bindings['vision'],(77,160,120))
        s.detach_preview(self.area,'vision');self.assertNotIn('vision',s.preview_bindings)
        s.attach_preview(self.area,'vision',160,120);self.callbacks.pop(0)()
        self.assertEqual(s.preview_output.attach.call_count,2);s.preview_output.detach.assert_called_once_with('vision')

    def test_deferred_bind_after_unmap_cannot_resurrect_view(self):
        s=self.stage;s.attach_preview(self.area,'vision',160,120);s.detach_preview(self.area,'vision')
        self.area.get_mapped.return_value=False;self.callbacks.pop(0)()
        s.preview_output.attach.assert_not_called()

    def test_obsolete_bind_after_same_xid_remap_is_discarded(self):
        s=self.stage;s.attach_preview(self.area,'vision',160,120);old=self.callbacks.pop(0)
        s.detach_preview(self.area,'vision');s.attach_preview(self.area,'vision',160,120)
        old();s.preview_output.attach.assert_not_called();self.callbacks.pop(0)()
        s.preview_output.attach.assert_called_once_with('vision',77,160,120)

    def test_unrealized_area_is_not_bound(self):
        self.area.get_realized.return_value=False
        self.stage.attach_preview(self.area,'vision',160,120);self.callbacks.pop(0)()
        self.stage.preview_output.attach.assert_not_called()

    def test_preview_close_and_unmap_are_idempotent_and_do_not_detach_other_name(self):
        s=self.stage;s.preview_bindings={'vision':(77,160,120),'large':(88,587,440)}
        s.detach_preview(self.area,'large');s.detach_preview(self.area,'large')
        self.assertEqual(s.preview_bindings,{'vision':(77,160,120)})
        self.assertEqual([call.args for call in s.preview_output.detach.call_args_list],[('large',),('large',)])

    def test_both_view_widgets_connect_real_unmap_handler(self):
        signals=[]
        for n in ast.walk(gtk_class):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='connect' and len(n.args)>=3:
                first,handler,name=n.args[:3]
                if (isinstance(first,ast.Constant) and first.value=='unmap' and isinstance(handler,ast.Attribute)
                        and handler.attr=='detach_preview' and isinstance(name,ast.Constant)):
                    signals.append(name.value)
        self.assertCountEqual(signals,['vision','large'])

    def test_continuous_missing_fresh_frame_keeps_canvas_mapped_without_rebind_loop(self):
        refresh=next(n for n in gtk_class.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_runtime')
        statements=[]
        for node in refresh.body:
            if (isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='image' for n in node.targets)):
                statements.append(node)
            if (isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
                    and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='set_visible'
                    and isinstance(node.value.func.value,ast.Attribute) and node.value.func.value.attr=='preview_image'):
                statements.append(node)
        self.assertEqual(len(statements),2)
        code=compile(ast.Module(body=statements,type_ignores=[]),'real-freshness-canvas-contract','exec')
        stage=self.stage;stage.preview_bindings={'vision':(77,160,120)}
        class Canvas:
            visible=True
            def get_window(self):return SimpleNamespace(xid=77)
            def get_realized(self):return True
            def get_mapped(self):return self.visible
            def set_visible(self,value):
                value=bool(value)
                if value==self.visible:return
                self.visible=value
                if value:stage.attach_preview(self,'vision',160,120)
                else:stage.detach_preview(self,'vision')
        stage.preview_image=Canvas()
        for _ in range(30):
            exec(code,{'self':stage,'display':{'frame_visible':False}})
            while self.callbacks:self.callbacks.pop(0)()
        self.assertTrue(stage.preview_image.get_mapped())
        stage.preview_output.detach.assert_not_called();stage.preview_output.attach.assert_not_called()
        self.assertEqual(stage.preview_bindings['vision'],(77,160,120))


if __name__=='__main__':unittest.main(verbosity=2)
