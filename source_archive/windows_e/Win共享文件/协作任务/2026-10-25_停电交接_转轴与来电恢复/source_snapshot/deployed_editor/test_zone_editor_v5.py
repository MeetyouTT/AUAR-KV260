import importlib.util,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch


class Node:
    def __init__(self,kind='',**options):
        self.kind=kind;self.options=options;self.calls=[];self.callbacks={};self.visible=False
        self.value=0.;self.native=types.SimpleNamespace(set_pass_through=lambda value:setattr(self,'pass_through',value))
    def __getattr__(self,name):
        def called(*args):
            self.calls.append((name,args))
            if name=='connect':self.callbacks[args[0]]=args[1:]
            elif name=='show_all':self.visible=True
            elif name=='hide':self.visible=False
            elif name=='set_value':self.value=args[0]
            elif name=='get_value':return self.value
            elif name=='get_window':return self.native
        return called


class RGBA:
    red=green=blue=0.
    def parse(self,value):self.red,self.green,self.blue=[int(value[i:i+2],16)/255 for i in [1,3,5]]


class Thread:
    def __init__(self,*args,**kwargs):pass
    def start(self):pass


def load_editor():
    gtk=types.SimpleNamespace(Window=lambda **k:Node('window',**k),DrawingArea=lambda **k:Node('drawing',**k),
        Box=lambda **k:Node('box',**k),Label=lambda **k:Node('label',**k),Button=lambda **k:Node('button',**k),
        Scale=types.SimpleNamespace(new_with_range=lambda *a:Node('scale')),WindowType=types.SimpleNamespace(POPUP='popup'),
        Orientation=types.SimpleNamespace(VERTICAL='vertical',HORIZONTAL='horizontal'))
    gdk=types.SimpleNamespace(RGBA=RGBA,EventMask=types.SimpleNamespace(BUTTON_PRESS_MASK=1,BUTTON_RELEASE_MASK=2,POINTER_MOTION_MASK=4))
    glib=types.SimpleNamespace(source_remove=lambda *_:None,timeout_add=lambda *_:1,idle_add=lambda fn,*a:fn(*a))
    gi=types.ModuleType('gi');gi.require_version=lambda *_:None
    repository=types.ModuleType('gi.repository');repository.Gtk,repository.Gdk,repository.GLib=gtk,gdk,glib
    spec=importlib.util.spec_from_file_location('zone_editor_v5_candidate',Path(__file__).with_name('face_zone_editor.py'))
    module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'gi':gi,'gi.repository':repository}):spec.loader.exec_module(module)
    return module


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.module=load_editor();self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'settings.json'
        self.original={'schema':'aura-face-zone-settings-1','left_ratio':0.,'left_camera_ratio':.1,
            'right_ratio':.7158253629442671,'viewport':[8,112,568,300],'board_boot_id':'old-test-boot',
            'extra_provenance':{'scope':'preserve-test'}}
        self.path.write_text(json.dumps(self.original))
        with patch.object(self.module.threading,'Thread',Thread):self.editor=self.module.Editor(self.path)
    def tearDown(self):self.temp.cleanup()
    def test_actual_content_mapping_puts_fixed_left_center_at_132(self):
        self.assertEqual(self.module.VIEW,(8,112,568,300));self.assertEqual(self.module.CONTENT,(92,112,400,300))
        self.assertEqual(self.editor.left_camera_ratio,.1)
        self.assertIn(('move',(130,112)),self.editor.left_line.calls)
        self.assertIn(('resize',(5,300)),self.editor.left_line.calls)
        self.assertAlmostEqual(self.module.image_ratio(self.editor.ratio),.8064720153808593)
    def test_left_line_is_passthrough_unfocusable_and_panel_initially_hidden(self):
        left=self.editor.left_line
        self.assertEqual(left.options['type'],'popup')
        self.assertIn(('set_accept_focus',(False,)),left.calls)
        self.assertIn('realize',left.callbacks)
        callback=left.callbacks['realize'][0];callback(left)
        self.assertTrue(left.pass_through)
        self.assertNotIn('button-press-event',left.callbacks)
        self.assertNotIn('motion-notify-event',left.callbacks)
        self.assertFalse(self.editor.panel.visible)
        self.assertFalse(self.editor.line.visible);self.assertFalse(left.visible)
    def test_both_lines_follow_vision_visibility_without_opening_panel(self):
        self.editor.update(True,None)
        self.assertTrue(self.editor.line.visible);self.assertTrue(self.editor.left_line.visible)
        self.assertFalse(self.editor.panel.visible)
        self.editor.update(False,None)
        self.assertFalse(self.editor.line.visible);self.assertFalse(self.editor.left_line.visible)
        self.assertFalse(self.editor.panel.visible)
    def test_right_save_and_drag_keep_left_camera_field_and_legacy_mapping(self):
        editor=self.editor;commands=[];editor.command=commands.append
        editor.set_ratio(self.module.widget_ratio(.7));editor.queue_save()
        self.assertEqual(editor.pending['left_camera_ratio'],.1);self.assertEqual(editor.pending['left_ratio'],0.)
        self.assertAlmostEqual(self.module.image_ratio(editor.pending['right_ratio']),.7)
        editor.press(None,None)
        editor.motion(None,types.SimpleNamespace(x_root=92+400*.82))
        editor.release();value=editor.pending
        self.assertEqual(value['left_camera_ratio'],.1);self.assertEqual(value['left_ratio'],0.)
        self.assertAlmostEqual(self.module.image_ratio(value['right_ratio']),.82)
        self.assertEqual(value['extra_provenance'],self.original['extra_provenance'])
        self.assertEqual(value['viewport'],[8,112,568,300]);self.assertEqual(value['frame_width'],640)
        self.assertEqual(value['frame_height'],480);self.assertTrue(value['mirror_horizontal'])
        self.assertEqual(value['target_kind'],'face');self.assertEqual(value['reference'],'face_center')
        self.assertEqual(value['board_boot_id'],Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        self.assertTrue(all(command=='pan_stop' for command in commands))
    def test_atomic_disk_save_preserves_left_and_right_and_permissions(self):
        editor=self.editor;editor.set_ratio(self.module.widget_ratio(.79));editor.queue_save()
        def idle(fn,*args):fn(*args);editor.closed.set()
        with patch.object(self.module.GLib,'idle_add',idle):editor.save_worker()
        value=json.loads(self.path.read_text())
        self.assertEqual(value['left_camera_ratio'],.1);self.assertEqual(value['left_ratio'],0.)
        self.assertAlmostEqual(self.module.image_ratio(value['right_ratio']),.79)
        self.assertEqual(value['extra_provenance'],self.original['extra_provenance'])
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
    def test_existing_left_value_is_retained_not_overwritten_to_default(self):
        self.original['left_camera_ratio']=.12;self.path.write_text(json.dumps(self.original))
        with patch.object(self.module.threading,'Thread',Thread):editor=self.module.Editor(self.path)
        self.assertEqual(editor.left_camera_ratio,.12)
        editor.set_ratio(self.module.widget_ratio(.75));editor.queue_save()
        self.assertEqual(editor.pending['left_camera_ratio'],.12)
        self.assertIn(('move',(138,112)),editor.left_line.calls)
    def test_legacy_settings_default_left_to_ten_percent_without_changing_right(self):
        self.original.pop('left_camera_ratio');self.path.write_text(json.dumps(self.original))
        with patch.object(self.module.threading,'Thread',Thread):editor=self.module.Editor(self.path)
        self.assertEqual(editor.pending['left_camera_ratio'],.1)
        self.assertEqual(editor.pending['right_ratio'],self.original['right_ratio'])


if __name__=='__main__':unittest.main()
