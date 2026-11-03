"""Preview the real GTK touchscreen layout without devices, models or services.

Run under a desktop display for interactive review, or under xvfb-run with
--snapshots DIR for native 1024x600 screenshots and geometry/navigation checks.
All dialogue, people and target data in this tool are explicitly examples.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0,str(AURA))

from tools.board_avatar_gtk import BoardAvatarStage, load_gtk, register_font
from board.interaction import avatar_board
from board.interaction.ui_services import ConnectionStore
from board.runtime.character import DEMO_LINES


class LayoutPreview:
    def __init__(self):
        self.gtk,self.gdk,self.pixbuf,self.glib = load_gtk()
        initialized = self.gtk.init_check([])
        if not initialized[0]:
            raise RuntimeError('GTK needs an X display; use xvfb-run for snapshots')
        register_font(AURA/'assets/fonts/DroidSansFallbackFull.ttf')
        self.directory = tempfile.TemporaryDirectory(prefix='aura-ui-preview-')
        self.reference = {'camera_epoch':'preview-only','frame_id':1,'captured_mono_ms':0}
        self.example = True
        stage = self.stage = BoardAvatarStage.__new__(BoardAvatarStage)
        stage.Gtk,stage.Gdk,stage.Pixbuf,stage.GLib = self.gtk,self.gdk,self.pixbuf,self.glib
        stage.character = '汐蓝'
        stage.layout,stage.tokens = avatar_board.load_layout(),avatar_board.load_tokens()
        stage.touch_layout = json.loads((AURA/'ui/board_touch_layout.json').read_text(encoding='utf-8'))
        stage.geometry = avatar_board.avatar_box(stage.layout)
        stage.rect = avatar_board.contain_rect(464,480,stage.geometry['w'],stage.geometry['h'])
        stage.preferences = {'volume':58,'muted':False,'fullscreen':False,'economy':False}
        stage.controls,stage.last_click = {},{}
        stage.updating_volume = stage.volume_dragging = False
        stage.input_events,stage.samples = deque(maxlen=200),deque()
        stage.lines,stage.touch_inputs = DEMO_LINES,[]
        stage.last_touch_scan = time.monotonic()+3600
        stage.last_service_result = stage.last_preview_key = None
        stage.preview_dialog = stage.large_preview = stage.large_preview_note = None
        stage.toast,stage.toast_until = '',0
        stage.reply_text = None
        stage.device_inventory = {'camera_present':False,'lan':None}
        stage.connection_store = ConnectionStore(Path(self.directory.name)/'connection.json')
        stage.services = SimpleNamespace(read=self.view)
        stage.preview_output = SimpleNamespace(attach=lambda *args:None,detach=lambda *args:None,
                                               read=lambda *args:self.display())
        stage.mixer = SimpleNamespace(read=lambda:{'available':True,'volume':58,'muted':False,
                                                   'pending':False,'error':''})
        stage.native = self.command
        stage.close = self.close
        stage.build_window(True)
        stage.window.set_decorated(False)
        stage.window.move(0,0)
        portrait = self.pixbuf.Pixbuf.new_from_file(str(AURA/'assets/avatar/idle_present/000000.png'))
        stage.portrait.set_from_pixbuf(portrait.scale_simple(stage.rect['w'],stage.rect['h'],self.pixbuf.InterpType.BILINEAR))
        self.sample_image = self.pixbuf.Pixbuf.new_from_file(str(AURA/'tests/fixtures/vision/person_bus.jpg'))
        stage.preview_image.connect('draw',self.draw_example)
        self.refresh()

    def view(self):
        modules = {'camera':{'state':'READY'},'vision':{'state':'READY','people_count':2},
                   'npu':{'state':'READY'},'pl':{'state':'UNKNOWN'},
                   'target':{'state':'CONFIRMED','selected':{'track_id':7}},
                   'identity':{'state':'UNKNOWN'},'host':{'state':'READY'},'audio':{'state':'READY'},
                   'interaction':{'state':'IDLE','transcript':'你好，汐蓝！今天我们可以聊些什么？',
                       'reply':'你好呀，很高兴见到你！\n我们可以聊聊今天的心情，也可以一起看看周围。你想先从什么开始？',
                       'timings_ms':{}}}
        snapshot = {'source_kind':'fixture','modules':modules,'preview':self.reference,
                    'capabilities':{'target_select':False,'ask_frame':False}}
        return {'snapshot':snapshot if self.example else None,'link':'READY' if self.example else 'OFFLINE',
                'connection':self.stage.connection_store.read(),'error':'','preview':None,'results':[],
                'pending_count':0,'ui_epoch':'preview-only','ui_generation':0}

    def display(self):
        return {'frame_visible':self.example,'frame_reference':self.reference if self.example else None}

    def refresh(self):
        self.reference['captured_mono_ms'] = int(time.monotonic()*1000)
        state = {'phase':'IDLE','paused':False,'playing':False,'error':'','avatar_command_pending':0,
                 'local_recording':{'state':'IDLE','can_start':True,'can_stop':False}}
        text = self.stage.refresh_settings(state)
        self.stage.refresh_runtime(state,text)
        self.stage.mode_label.set_text('界面预览 · '+('对话和画面均为示例' if self.example else '未连接状态示例'))
        return True

    def command(self, data):
        kind = data.get('type')
        if kind in ('ui_page','ui_layer'):
            result = self.stage.command(data)
            self.refresh()
            return result
        if kind == 'preview_open':
            result = self.stage.open_preview()
            self.stage.large_preview.connect('draw',self.draw_example)
            self.stage.large_preview_note.set_text('示例画面 · 非实时摄像头')
            return result
        return {'ok':True,'message':'界面预览：此操作不访问设备或服务'}

    def draw_example(self, area, context):
        if not self.example:return False
        width,height = area.get_allocated_width(),area.get_allocated_height()
        source = self.sample_image
        scale = max(width/source.get_width(),height/source.get_height())
        context.save()
        context.rectangle(0,0,width,height)
        context.clip()
        context.translate((width-source.get_width()*scale)/2,(height-source.get_height()*scale)/2)
        context.scale(scale,scale)
        self.gdk.cairo_set_source_pixbuf(context,source,0,0)
        context.paint()
        context.restore()
        # Hand-positioned illustrative overlays, never presented as detections.
        for x,y,w,h,label in ((.05,.28,.27,.71,'# 12'),(.34,.28,.24,.71,'# 7')):
            context.set_source_rgb(.18,.86,.69)
            context.set_line_width(2)
            context.rectangle(x*width,y*height,w*width,h*height)
            context.stroke()
            context.select_font_face('Sans')
            context.set_font_size(15)
            context.move_to(x*width+6,y*height+19)
            context.show_text(label)
        context.set_source_rgba(0,0,0,.65)
        context.rectangle(0,0,width,28)
        context.fill()
        context.set_source_rgb(1,1,1)
        context.set_font_size(13)
        context.move_to(10,19)
        context.show_text('PREVIEW / SAMPLE IMAGE')
        return False

    def drain(self):
        for _ in range(12):
            while self.gtk.events_pending():self.gtk.main_iteration_do(False)
            time.sleep(.008)

    def snapshots(self, output):
        output.mkdir(parents=True,exist_ok=True)
        stage = self.stage
        report = {'scope':'HOST_GTK_PREVIEW_ONLY','board_deployed':False,'example_data':True,
                  'pages':{},'checks':[]}
        def save(name):
            self.refresh();self.drain()
            rect = stage.window.get_allocation()
            assert (rect.width,rect.height) == (1024,600),(name,rect.width,rect.height)
            shot = self.gdk.pixbuf_get_from_window(stage.window.get_window(),0,0,1024,600)
            shot.savev(str(output/(name+'.png')),'png',[],[])
            widgets = {}
            for key,control in stage.controls.items():
                if not control.get_mapped():continue
                box = control.get_allocation()
                x,y = control.translate_coordinates(stage.fixed,0,0)[-2:]
                assert 0 <= x and 0 <= y and x+box.width <= 1024 and y+box.height <= 600,(name,key,x,y,box.width,box.height)
                assert box.height >= (40 if key == 'layer_switch' else 48),(key,box.height)
                widgets[key] = {'x':x,'y':y,'width':box.width,'height':box.height}
            report['pages'][name] = {'layer':stage.ui_layer,'page':stage.page,'width':rect.width,'height':rect.height,'controls':widgets}

        for page in ('main','vision'):
            stage.show_page(page);save(page)
            assert stage.navigation_panels['presentation'].get_mapped()
            assert not stage.navigation_panels['debug'].get_mapped()
            assert stage.preview_image.get_mapped() == (page == 'vision')
            assert stage.portrait.get_mapped() == (page != 'vision')
            assert stage.vision_insights.get_mapped() == (page == 'vision')
        # Exercise actual native button callbacks, including return to vision.
        stage.controls['vision_settings'].clicked();self.drain()
        assert stage.page == 'settings' and stage.ui_layer == 'presentation'
        save('presentation_settings')
        stage.controls['layer_switch'].clicked();self.drain()
        assert stage.page == 'devices' and stage.ui_layer == 'debug'
        save('debug_devices')
        time.sleep(.26)
        stage.controls['layer_switch'].clicked();self.drain()
        assert stage.page == 'vision' and stage.ui_layer == 'presentation'
        report['checks'].append('native_layer_switch_restores_last_presentation_page')
        for page in ('demo','devices','connection','settings'):
            stage.show_layer('debug');stage.show_page(page);save('debug_'+page)
            assert stage.navigation_panels['debug'].get_mapped()
            assert not stage.navigation_panels['presentation'].get_mapped()
        self.example = False
        for page in ('main','vision'):
            stage.show_page(page);save('offline_'+page)
            assert not stage.controls['ask_frame'].get_sensitive()
            assert not stage.controls['vision_target_select'].get_sensitive()
        report['checks'].extend(['all_pages_1024x600','visible_controls_inside_canvas',
                                 'presentation_hides_debug_navigation','camera_only_on_vision',
                                 'settings_accessible_without_debug','offline_actions_disabled'])
        (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return report

    def close(self, *unused):
        self.stage.window.destroy()
        if self.gtk.main_level():self.gtk.main_quit()
        self.directory.cleanup()
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshots',type=Path)
    args = parser.parse_args(argv)
    preview = LayoutPreview()
    try:
        if args.snapshots:
            report = preview.snapshots(args.snapshots)
            print(json.dumps({'status':'PASS','pages':len(report['pages']),'checks':report['checks'],
                              'output':str(args.snapshots)},ensure_ascii=False))
        else:
            preview.glib.timeout_add(250,preview.refresh)
            preview.gtk.main()
    finally:
        preview.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
