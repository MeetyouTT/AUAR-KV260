#!/usr/bin/env python3
"""Host GTK geometry checks only: no model, mixer, microphone or board access."""
from collections import deque
import json
from pathlib import Path
import sys
import tempfile
import time
import types

REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(REPO))
from tools.board_avatar_gtk import BoardAvatarStage, load_gtk, register_font
from board.interaction import avatar_board
from board.interaction.ui_services import ConnectionStore


def main():
    output = Path(__file__).resolve().parent/'host-layout'
    output.mkdir(exist_ok=True)
    gtk,gdk,pixbuf,glib = load_gtk()
    assert gtk.init_check([])[0]
    register_font(REPO/'assets/fonts/DroidSansFallbackFull.ttf')
    stage = BoardAvatarStage.__new__(BoardAvatarStage)
    stage.Gtk,stage.Gdk,stage.Pixbuf,stage.GLib = gtk,gdk,pixbuf,glib
    stage.character = '汐蓝'
    stage.layout,stage.tokens = avatar_board.load_layout(),avatar_board.load_tokens()
    stage.touch_layout = json.loads((REPO/'ui/board_touch_layout.json').read_text())
    stage.geometry = avatar_board.avatar_box(stage.layout)
    stage.rect = avatar_board.contain_rect(464,480,stage.geometry['w'],stage.geometry['h'])
    stage.preferences = {'volume':18,'muted':False,'fullscreen':True,'economy':True}
    stage.controls,stage.last_click = {},{}
    stage.updating_volume = stage.volume_dragging = False
    stage.input_events = deque(maxlen=200)
    stage.lines = [{'label':x} for x in ('打招呼','开心回应','认真说明','温柔安慰')]
    stage.touch_inputs = []
    stage.last_touch_scan = time.monotonic()
    stage.last_preview_key = stage.last_service_result = None
    stage.preview_times = deque(maxlen=120)
    stage.preview_frame_count = 0
    stage.preview_dialog = stage.large_preview = stage.large_preview_note = None
    stage.preview_output = None
    stage.toast,stage.toast_until = '',0
    stage.samples = deque()
    stage.device_inventory = {'camera_present':False,'lan':None}
    settings = {'available':True,'volume':18,'muted':False,'pending':False,'error':''}
    stage.mixer = types.SimpleNamespace(read=lambda:dict(settings))
    with tempfile.TemporaryDirectory() as directory:
        stage.connection_store = ConnectionStore(Path(directory)/'connection.json')
        stage.services = types.SimpleNamespace(read=lambda:{'snapshot':None,'connection':stage.connection_store.read(),
            'link':'DISABLED','error':'','preview':None,'preview_error':'','results':[],
            'pending_count':0,'ui_epoch':'host-layout-only','ui_generation':0})
        stage.build_window(False)
        portrait = pixbuf.Pixbuf.new_from_file(str(REPO/'assets/avatar/idle_present/000000.png'))
        stage.portrait.set_from_pixbuf(portrait.scale_simple(stage.rect['w'],stage.rect['h'],pixbuf.InterpType.BILINEAR))
        def drain():
            for _ in range(20):
                while gtk.events_pending():gtk.main_iteration_do(False)
                time.sleep(.005)
        drain()
        assert stage.preview_image.get_allocated_width()==197,stage.preview_image.get_allocation()
        state = {'phase':'IDLE','paused':False,'playing':False,'error':''}
        text = stage.refresh_settings(state)
        stage.refresh_runtime(state,text)
        drain()
        report = {'scope':'HOST_GTK_LAYOUT_ONLY_NOT_BOARD_ACCEPTANCE','pages':{},'controls':{}}
        for page in stage.page_names:
            stage.show_page(page);drain()
            allocation = stage.window.get_allocation()
            report['pages'][page] = {'width':allocation.width,'height':allocation.height}
            shot = gdk.pixbuf_get_from_window(stage.window.get_window(),0,0,allocation.width,allocation.height)
            shot.savev(str(output/(page+'.png')),'png',[],[])
            assert (allocation.width,allocation.height) == (1024,600),report['pages']
            for name,control in stage.controls.items():
                if not control.get_mapped():continue
                rect = control.get_allocation()
                xy = control.translate_coordinates(stage.fixed,0,0)
                x,y = xy[-2:]
                report['controls'][name] = {'page':page,'x':x,'y':y,'width':rect.width,'height':rect.height,
                                           'sensitive':control.get_sensitive()}
                assert rect.height >= 48,(name,rect.height)
                assert 0 <= x and 0 <= y and x+rect.width <= 585 and y+rect.height <= 556,(name,report['controls'][name])
        assert not stage.controls['record'].get_sensitive()
        assert not stage.controls['identity_delete'].get_sensitive()
        from tools.board_screen_capture import capture
        assert capture(output/'x11-screen.png') == (1024,600)
        stage.open_preview();drain()
        rect = stage.preview_dialog.get_allocation()
        report['large_preview'] = {'width':rect.width,'height':rect.height}
        assert rect.width<=1024 and rect.height<=600,report['large_preview']
        stage.preview_dialog.response(gtk.ResponseType.CLOSE);drain()
        stage.show_page('connection');drain()
        def capture_dialog():
            dialog = next(w for w in gtk.Window.list_toplevels() if w != stage.window and w.get_visible())
            rect = dialog.get_allocation()
            assert rect.width <= 1024 and rect.height <= 600
            shot = gdk.pixbuf_get_from_window(dialog.get_window(),0,0,rect.width,rect.height)
            shot.savev(str(output/'touch-keypad.png'),'png',[],[])
            report['keypad'] = {'width':rect.width,'height':rect.height}
            dialog.response(gtk.ResponseType.CANCEL)
            return False
        glib.timeout_add(180,capture_dialog)
        assert stage.keyboard_dialog('输入服务 IPv4 地址','127.0.0.1') is None
        (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))
        stage.window.destroy()
    import runpy
    runpy.run_path(str(Path(__file__).with_name('preview_native_host.py')),run_name='__main__')
    return 0


if __name__ == '__main__':
    sys.exit(main())
