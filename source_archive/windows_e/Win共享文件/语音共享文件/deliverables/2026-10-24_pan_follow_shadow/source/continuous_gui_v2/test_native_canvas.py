import importlib.util,sys,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

class NativeCanvasTests(unittest.TestCase):
    def test_native_redraw_only_uses_current_unexpired_output(self):
        with patch.dict(sys.modules,{'tools.pan_controls':SimpleNamespace(stage_type=lambda base,factory:base)}):
            s=importlib.util.spec_from_file_location('gui_canvas',Path(__file__).parent/'face_pan_controls.py')
            m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        Stage=m.stage_type(object,lambda:None);stage=Stage.__new__(Stage);events=[]
        out={'lifecycle_lock':threading.Lock(),'reference':{'captured_mono_ms':int(time.monotonic()*1000)-80},
            'cleared':False,'pipeline':SimpleNamespace(get_by_name=lambda _: 'sink')}
        overlay=SimpleNamespace(set_render_rectangle=lambda *x:events.append(('rectangle',x)),expose=lambda *x:events.append(('expose',x)))
        stage.preview_output=SimpleNamespace(lock=threading.Lock(),outputs={'vision':out},is_current=lambda n,o:o is out,
            GstVideo=SimpleNamespace(VideoOverlay=overlay))
        area=SimpleNamespace(get_mapped=lambda:True,get_allocated_width=lambda:568,get_allocated_height=lambda:300)
        self.assertFalse(stage.face_native_expose(area,'vision'));self.assertEqual([x[0] for x in events],['rectangle','expose'])
        for state in ('expired','cleared','detached','unmapped'):
            events.clear();out['reference']['captured_mono_ms']=int(time.monotonic()*1000)-(300 if state=='expired' else 30)
            out['cleared']=state=='cleared';stage.preview_output.outputs={} if state=='detached' else {'vision':out}
            if state=='detached':stage.preview_output.is_current=lambda n,o:False
            else:stage.preview_output.is_current=lambda n,o:True
            area.get_mapped=lambda:state!='unmapped'
            stage.face_native_expose(area,'vision');self.assertEqual(events,[],state)

if __name__=='__main__':unittest.main()
