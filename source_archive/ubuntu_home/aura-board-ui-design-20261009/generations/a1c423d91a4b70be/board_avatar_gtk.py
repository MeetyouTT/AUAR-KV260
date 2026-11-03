"""KV260 touchscreen shell, cached avatar playback and asynchronous service ports."""
import argparse
from collections import deque
import ctypes
import ctypes.util
import hashlib
import io
import json
from pathlib import Path
import queue
import sys
import time

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
DEFAULT_ROOT = AURA.parent / 'deliverables/2026-10-06_xilan_live'
DEFAULT_CONFIG = AURA / 'config/board_avatar_gtk.json'


def register_font(path):
    """Register a bundled font for this process, without changing system fonts."""
    path = Path(path).resolve(strict=True)
    library = ctypes.util.find_library('fontconfig')
    if not library:
        raise RuntimeError('Fontconfig library is unavailable')
    fc = ctypes.CDLL(library)
    fc.FcConfigAppFontAddFile.argtypes = (ctypes.c_void_p, ctypes.c_char_p)
    fc.FcConfigAppFontAddFile.restype = ctypes.c_int
    if not fc.FcConfigAppFontAddFile(None, str(path).encode()):
        raise RuntimeError('Cannot register bundled Chinese font')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gtk():
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
    return Gtk, Gdk, GdkPixbuf, GLib


class BoardAvatarStage:
    def __init__(self, root, config, evidence_root, *, windowed=False, settings_file=None):
        from PIL import Image
        from board.interaction import avatar_board
        from board.runtime.character import CHARACTER_NAME, DEMO_LINES
        from tools.demo_script import create_demo_core
        from tools.gstreamer_audio import GStreamerAudioOutput
        from tools.realtime_bridge import StageBridge
        from tools.realtime_controller import RealtimeController
        from tools.selected_voice_service import SpeechJobs, VoiceWorker
        from tools.pillow_compat import LANCZOS
        from tools.board_ui_settings import MixerService, SettingsStore
        from board.interaction.ui_services import ConnectionStore, UiServiceClient

        self.Image, self.LANCZOS = Image, LANCZOS
        self.Gtk, self.Gdk, self.Pixbuf, self.GLib = load_gtk()
        self.root = Path(root).resolve(strict=True)
        self.evidence_root = Path(evidence_root)
        self.evidence_root.mkdir(parents=True, exist_ok=False)
        self.lines, self.character = DEMO_LINES, CHARACTER_NAME
        self.layout, self.tokens = avatar_board.load_layout(), avatar_board.load_tokens()
        self.touch_layout = json.loads((AURA/'ui/board_touch_layout.json').read_text(encoding='utf-8'))
        self.geometry = avatar_board.avatar_box(self.layout)
        self.rect = avatar_board.contain_rect(464, 480, self.geometry['w'], self.geometry['h'])
        self.source_hashes = {}
        for name in ('board_avatar_gtk.py', 'gstreamer_audio.py', 'gstreamer_audio_engine.py',
                     'gstreamer_audio_worker.py', 'realtime_audio.py', 'realtime_controller.py',
                     'realtime_facials.py', 'facial_layers.py', 'pillow_compat.py', 'selected_voice_service.py',
                     'board_ui_settings.py', 'x11_foreground.py'):
            self.source_hashes['tools/' + name] = hashlib.sha256((AURA/'tools'/name).read_bytes()).hexdigest()
        reuse = AURA.parent/'deliverables/2026-10-06_avatar_reuse/preview_script.py'
        self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py'] = hashlib.sha256(reuse.read_bytes()).hexdigest()
        for name in ('ui_contract.py', 'ui_services.py'):
            rel = 'board/interaction/'+name
            self.source_hashes[rel] = hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        for rel in ('ui/board_touch_layout.json','config/board_ui_services.json'):
            self.source_hashes[rel] = hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        self.config = config
        self.font_hash = register_font(AURA/config['font_file'])
        initialized = self.Gtk.init_check([])
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            raise RuntimeError('Cannot connect to the current X display')
        self.jobs = self.output = self.bridge = self.mixer = self.services = None
        self.settings_store = SettingsStore(settings_file or AURA.parent/'avatar_user_settings.json')
        self.preferences = self.settings_store.read()
        if windowed:
            self.preferences['fullscreen'] = False
        self.input_events = deque(maxlen=200)
        self.controls = {}
        self.last_click = {}
        self.updating_volume = self.volume_dragging = False
        self.last_touch_scan = 0
        self.touch_inputs = []
        self.device_inventory = {'camera_present':False, 'lan':None}
        self.page = 'main'
        self.runtime_view = {}
        self.last_preview_key = None
        self.last_service_result = None
        self.toast, self.toast_until = '', 0
        self.closed = False
        self.errors, self.samples = [], deque(maxlen=10000)
        self.last_tick = self.last_publish = None
        self.last_image = self.current_pixbuf = None
        self.timer = self.foreground_timer = None
        try:
            core = create_demo_core('reuse')
            core.MAX_CACHED_SEQUENCES = int(config['cache_sequences'])
            self.jobs = SpeechJobs(self.root, VoiceWorker(self.root, cached_only=True))
            self.output = GStreamerAudioOutput(self.evidence_root/'audio_worker.log', config['audio_device'])
            self.controller = RealtimeController(core, self.jobs, self.output)
            self.mixer = MixerService(self.settings_store)
            defaults = json.loads((AURA/'config/board_ui_services.json').read_text(encoding='utf-8'))
            self.connection_store = ConnectionStore(AURA.parent/'avatar_service_settings.json', defaults['connection'])
            self.board_boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            self.services = UiServiceClient(self.board_boot_id, self.connection_store.read())
            self.bridge = StageBridge(self.root, int(config['browser_port']),
                                      extra_commands=('ui_settings', 'ui_page', 'ui_service_config',
                                                      'service_action', 'ui_refresh'))
            self.build_window(windowed)
            self.schedule_tick()
            self.foreground_timer = self.GLib.timeout_add(500, self.present_window)
        except Exception:
            self.cleanup()
            raise

    def label(self, text, x, y, width, height, name=None, parent=None):
        label = self.Gtk.Label(label=text)
        label.set_xalign(0)
        label.set_yalign(0.5)
        label.set_line_wrap(True)
        if name:
            label.set_name(name)
        label.set_size_request(width, height)
        (parent if parent is not None else self.fixed).put(label, x, y)
        return label

    def button(self, label, data, x, y, width, height, parent=None, key=None):
        button = self.Gtk.Button(label=label)
        button.set_size_request(width, height)
        button.set_can_focus(False)
        button.add_events(self.Gdk.EventMask.TOUCH_MASK)
        button.connect('touch-event', self.observe_touch, label)
        button.connect('clicked', self.activated, data, key or label)
        (parent if parent is not None else self.fixed).put(button, x, y)
        self.controls[key or label] = button
        return button

    def observe_touch(self, widget, event, label):
        if widget is getattr(self,'volume_scale',None):
            if event.type == self.Gdk.EventType.TOUCH_BEGIN:
                self.volume_dragging = True
            elif event.type in (self.Gdk.EventType.TOUCH_END,self.Gdk.EventType.TOUCH_CANCEL):
                self.volume_dragging = False
        if event.type in (self.Gdk.EventType.TOUCH_BEGIN, self.Gdk.EventType.TOUCH_END,
                          self.Gdk.EventType.TOUCH_CANCEL):
            self.input_events.append({'kind': 'touch', 'event': event.type.value_nick,
                                      'button': label, 'at': time.monotonic()})
        # GTK owns the gesture and emits one clicked signal on activation.
        return False

    def activated(self, widget, data, key):
        now = time.monotonic()
        if now-self.last_click.get(key, -1) < .25:
            return
        self.last_click[key] = now
        self.input_events.append({'kind': 'activation', 'button': key, 'at': now})
        result = self.native(data)
        self.toast = result.get('error', '') if not result.get('ok') else result.get('message', '操作已响应')
        self.toast_until = now+1.5

    def schedule_tick(self):
        if self.timer:
            self.GLib.source_remove(self.timer)
        interval = 250 if self.preferences['economy'] else int(self.config['tick_ms'])
        self.timer = self.GLib.timeout_add(interval, self.tick,
                                         priority=self.GLib.PRIORITY_DEFAULT_IDLE)

    def present_window(self):
        self.foreground_timer = None
        try:
            from tools.x11_foreground import raise_owned_window
            info = raise_owned_window(self.window)
            print('FOREGROUND '+json.dumps(info), flush=True)
        except Exception as exc:
            self.errors.append('前景窗口：'+str(exc))
        return False

    def build_window(self, windowed):
        gtk = self.Gtk
        width, height = self.layout['canvas']['width'], self.layout['canvas']['height']
        self.window = gtk.Window(title=self.character)
        self.window.set_default_size(width, height)
        self.window.set_resizable(False)
        self.window.connect('delete-event', lambda *unused: self.close())
        self.window.connect('key-press-event', self.key_pressed)
        self.fixed = gtk.Fixed()
        self.fixed.set_size_request(width, height)
        self.window.add(self.fixed)
        colors = self.tokens['colors']
        css = ('window {background:'+colors['panel_bg']+';color:'+colors['text_primary']+';font:16px "Droid Sans Fallback";}'
               'button {padding:6px;border-radius:9px;font-size:18px;background:'+colors['bg']+';color:'+colors['text_primary']+';}'
               'button:active, button.selected {background:'+colors['accent']+';color:white;}'
               'button:disabled {color:#91969b;background:#ebede8;}'
               'button.primary {background:'+colors['accent']+';color:white;}'
               'button.primary:disabled {background:#e4e8e3;color:#91969b;}'
               'button.danger {color:'+colors['error']+';}'
               'button.nav {font-size:17px;}'
               'entry {font-size:22px;padding:5px;border-radius:8px;}'
               'textview, textview text {background:'+colors['bg']+';color:'+colors['text_primary']+';font-size:18px;}'
               '.card {background:'+colors['bg']+';border-radius:9px;}'
               'label.muted {color:'+colors['text_secondary']+';font-size:13px;}'
               'label.card_title {color:'+colors['text_secondary']+';font-size:13px;}'
               'label.card_value {font-size:19px;}'
               'label.good {color:'+colors['success']+';}'
               'label.warn {color:'+colors['warning']+';}'
               'label.bad {color:'+colors['error']+';}'
               'label.unknown {color:'+colors['text_secondary']+';}'
               'scale slider {min-width:32px;min-height:32px;}'
               'scale trough {min-height:8px;}'
               '#title {font-size:24px;color:'+colors['accent_dark']+';}'
               '#avatar_title {color:'+colors['text_secondary']+';}'
               '#status {font-size:21px;color:'+colors['accent_dark']+';}'
               '#footer {font-size:14px;}')
        provider = gtk.CssProvider()
        provider.load_from_data(css.encode())
        gtk.StyleContext.add_provider_for_screen(self.Gdk.Screen.get_default(), provider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        pad = self.layout['left_panel']['padding']
        left_width = self.layout['left_panel']['x1'] - pad*2
        spec = self.touch_layout
        if (spec['schema_version'] != 'aura-touch-layout-1' or spec['canvas'] != self.layout['canvas']
                or spec['page']['width'] != left_width or spec['page']['x'] != pad
                or spec['page']['y']+spec['page']['height'] > self.layout['top_area']['y1']):
            raise ValueError('触屏页面与板端布局合同不一致')
        self.label('AURA · '+self.character, pad, 6, left_width, 32, 'title')
        self.mode_label = self.label('本地演示可用 · 语音与视觉待接入', pad, 36, left_width, 18)
        self.mode_label.get_style_context().add_class('muted')
        button_width = (left_width-12)//2
        names = [('main','互动'), ('demo','演示'), ('devices','设备'), ('connection','连接'), ('settings','设置')]
        self.page_names = [row[0] for row in names]
        if self.page_names != spec['pages']:
            raise ValueError('触屏页面清单不一致')
        nav = spec['navigation']
        tab_width = (left_width-4*nav['gap'])//5
        for index,(name,title) in enumerate(names):
            item = self.button(title, {'type':'ui_page','page':name}, pad+index*(tab_width+nav['gap']), nav['y'],
                               tab_width, nav['height'], key='page_'+name)
            item.get_style_context().add_class('nav')
        self.pages = gtk.Stack()
        self.pages.set_size_request(left_width, spec['page']['height'])
        self.fixed.put(self.pages, spec['page']['x'], spec['page']['y'])
        page_widgets = {name:gtk.Fixed() for name in self.page_names}
        for name,page in page_widgets.items():
            page.set_size_request(left_width,spec['page']['height'])
            self.pages.add_named(page,name)
        main, demo, devices, connection, settings = [page_widgets[n] for n in self.page_names]
        slots = spec['main']
        self.status = self.label('语音与视觉待接入', 0, slots['status']['y'], left_width, slots['status']['height'], 'status', main)
        self.preview_box = gtk.EventBox()
        self.preview_box.get_style_context().add_class('card')
        self.preview_box.set_size_request(left_width,slots['preview']['height'])
        overlay = gtk.Overlay()
        self.preview_image = gtk.Image()
        overlay.add(self.preview_image)
        self.preview_placeholder = gtk.Label(label='等待视觉画面\n接入后显示当前画面与目标')
        self.preview_placeholder.set_justify(gtk.Justification.CENTER)
        overlay.add_overlay(self.preview_placeholder)
        self.preview_box.add(overlay)
        main.put(self.preview_box,0,slots['preview']['y'])
        self.target_label = self.label('目标待接入 · 身份待接入',0,slots['target']['y'],left_width,slots['target']['height'],parent=main)
        self.transcript_label = self.label('你说：—',0,slots['transcript']['y'],left_width,slots['transcript']['height'],parent=main)
        self.transcript_label.set_line_wrap(False)
        self.transcript_label.set_ellipsize(3)
        scroll = gtk.ScrolledWindow()
        scroll.set_size_request(left_width,slots['reply']['height'])
        scroll.set_policy(gtk.PolicyType.NEVER,gtk.PolicyType.AUTOMATIC)
        self.reply_view = gtk.TextView()
        self.reply_view.set_editable(False)
        self.reply_view.set_cursor_visible(False)
        self.reply_view.set_wrap_mode(gtk.WrapMode.WORD_CHAR)
        self.reply_view.set_left_margin(10)
        self.reply_view.set_right_margin(10)
        self.reply_view.set_top_margin(7)
        scroll.add(self.reply_view)
        main.put(scroll,0,slots['reply']['y'])
        self.reply_text = None
        self.latency_label = self.label('首声 — · ASR — · VLM — · TTS —',0,slots['latency']['y'],left_width,slots['latency']['height'],parent=main)
        self.latency_label.get_style_context().add_class('muted')
        third = (left_width-24)//3
        action_y,action_h = slots['actions']['y'],slots['actions']['height']
        self.record_button = self.button('开始录音',{'type':'record_toggle'},0,action_y,third,action_h,main,'record')
        self.record_button.get_style_context().add_class('primary')
        self.ask_button = self.button('当前图问答',{'type':'service_action','action':'ask_frame'},third+12,
                                      action_y,third,action_h,main,'ask_frame')
        self.interaction_cancel = self.button('取消本轮',{'type':'event','event':'cancel'},2*(third+12),
                                               action_y,third,action_h,main,'interaction_cancel')
        self.interaction_cancel.get_style_context().add_class('danger')
        self.demo_status = self.label('本地缓存演示',0,0,left_width,34,'status',demo)
        self.reply = self.label('选择台词即可播放已保存的汐蓝声音。',0,40,left_width,74,parent=demo)
        for index,line in enumerate(self.lines):
            self.button(line['label'], {'type':'demo','index':index}, (index%2)*(button_width+12),
                        120+(index//2)*76, button_width, 64, demo, 'demo_'+str(index))
        self.pause_button = self.button('暂停', {'type':'pause'}, 0, 276, button_width, 64, demo, 'pause')
        self.cancel_button = self.button('打断', {'type':'event','event':'cancel'}, button_width+12,
                                         276, button_width, 64, demo, 'cancel')
        self.button('重新开始', {'type':'event','event':'reset'}, 0, 356, button_width, 64, demo, 'reset')
        self.button('保存画面', {'type':'save_evidence'}, button_width+12, 356, button_width, 64, demo, 'save')
        self.device_cards = {}
        for index,(key,title) in enumerate([('camera','相机'),('vision','视觉'),('target','目标'),
                ('identity','身份'),('motion','运动'),('host','语音主机'),('audio','音频'),
                ('touch','触屏'),('network','有线网络')]):
            card = gtk.EventBox()
            card.get_style_context().add_class('card')
            card.set_size_request(third,78)
            inner = gtk.Fixed()
            card.add(inner)
            self.label(title,10,4,third-20,22,parent=inner).get_style_context().add_class('card_title')
            value = self.label('待接入',10,30,third-20,36,parent=inner)
            value.set_line_wrap(False)
            value.set_ellipsize(3)
            value.get_style_context().add_class('card_value')
            self.device_cards[key] = value
            devices.put(card,(index%3)*(third+12),(index//3)*86)
        self.device_note = self.label('服务尚未接入。',0,258,left_width,34,parent=devices)
        self.device_note.get_style_context().add_class('muted')
        for index,(label,action) in enumerate([('选择目标','target_select'),('登记身份','identity_enroll'),('删除身份','identity_delete')]):
            self.button(label,{'type':'service_dialog','action':action},index*(third+12),302,
                        third,56,devices,action)
        self.button('刷新状态',{'type':'ui_refresh'},0,376,button_width,56,devices,'refresh')
        self.button('保存诊断',{'type':'save_evidence'},button_width+12,376,button_width,56,devices,'diagnostics')
        self.label('服务连接',0,0,left_width,32,'status',connection)
        self.label('连接后开放录音、当前图问答与身份操作。',0,40,left_width,36,parent=connection)
        self.label('板端服务 IPv4 地址',0,88,left_width,26,parent=connection)
        self.host_entry = gtk.Entry()
        self.host_entry.set_size_request(left_width-108,52)
        self.host_entry.set_text(self.connection_store.read()['host'])
        connection.put(self.host_entry,0,118)
        self.button('输入',{'type':'ui_edit','field':'host'},left_width-96,118,96,52,connection,'edit_host')
        self.label('端口',0,182,left_width,26,parent=connection)
        self.port_entry = gtk.Entry()
        self.port_entry.set_size_request(left_width-108,52)
        self.port_entry.set_text(str(self.connection_store.read()['port']))
        connection.put(self.port_entry,0,212)
        self.button('输入',{'type':'ui_edit','field':'port'},left_width-96,212,96,52,connection,'edit_port')
        self.button('保存并连接',{'type':'connection_apply','enabled':True},0,286,
                    button_width,56,connection,'connect').get_style_context().add_class('primary')
        self.button('断开连接',{'type':'connection_apply','enabled':False},button_width+12,286,
                    button_width,56,connection,'disconnect')
        self.connection_label = self.label('尚未启用连接',0,352,left_width,48,parent=connection)
        self.host_status_label = self.label('语音主机：待接入',0,408,left_width,24,parent=connection)
        self.host_status_label.get_style_context().add_class('muted')
        self.volume_label = self.label('读取音量…', 0, 0, left_width, 36, parent=settings)
        self.button('-', {'type':'volume_step','delta':-10}, 0, 44, 64, 64, settings, 'volume_less')
        self.volume_scale = gtk.Scale.new_with_range(gtk.Orientation.HORIZONTAL,0,100,1)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_size_request(left_width-152,64)
        self.volume_scale.add_events(self.Gdk.EventMask.TOUCH_MASK)
        self.volume_scale.connect('touch-event',self.observe_touch,'音量')
        self.volume_scale.set_value(self.preferences['volume'])
        self.volume_scale.connect('value-changed',self.volume_changed)
        self.volume_scale.connect('button-press-event',self.volume_drag,True)
        self.volume_scale.connect('button-release-event',self.volume_drag,False)
        settings.put(self.volume_scale,76,44)
        self.button('+', {'type':'volume_step','delta':10}, left_width-64,44,64,64,settings,'volume_more')
        self.mute_button = self.button('静音', {'type':'toggle_setting','key':'muted'},0,120,
                                       left_width,56,settings,'mute')
        self.label('界面',0,188,left_width,32,parent=settings)
        self.fullscreen_button = self.button('退出全屏',{'type':'toggle_setting','key':'fullscreen'},
                                             0,228,button_width,56,settings,'fullscreen')
        self.economy_button = self.button('省电动画：关',{'type':'toggle_setting','key':'economy'},
                                          button_width+12,228,button_width,56,settings,'economy')
        self.devices_label = self.label('',0,296,left_width,60,parent=settings)
        self.button('恢复默认设置',{'type':'restore_settings'},0,368,left_width,56,settings,'restore_settings')
        panel = self.layout['right_panel']
        self.label(self.character, panel['x0']+panel['padding'], panel['y0']+panel['padding'],
                   panel['x1']-panel['x0']-2*panel['padding'], self.layout['right_inner']['label_h'], 'avatar_title')
        self.portrait = gtk.Image()
        self.fixed.put(self.portrait, self.geometry['x']+self.rect['x'], self.geometry['y']+self.rect['y'])
        bar = self.layout['bottom_bar']
        self.footer = self.label('正在读取设备状态…', 8, bar['y0']+4, width-16, bar['height']-8,'footer')
        self.footer.set_line_wrap(False)
        self.footer.set_ellipsize(3)
        self.window.show_all()
        self.show_page('main')
        if self.preferences['fullscreen']:
            self.window.fullscreen()

    def show_page(self, page):
        if page not in self.page_names:
            raise ValueError('未知页面')
        self.page = page
        self.pages.set_visible_child_name(page)
        for name in self.page_names:
            style = self.controls['page_'+name].get_style_context()
            (style.add_class if page == name else style.remove_class)('selected')

    def volume_drag(self, widget, event, dragging):
        self.volume_dragging = dragging
        return False

    def keyboard_dialog(self, title, initial='', field='host', accept='确定'):
        """Large native keys keep IPv4/port and future enrollment usable by touch."""
        gtk = self.Gtk
        dialog = gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.set_decorated(False)
        dialog.set_border_width(14)
        box = dialog.get_content_area()
        box.set_spacing(8)
        heading = gtk.Label(label=title)
        box.pack_start(heading,False,False,0)
        entry = gtk.Entry()
        entry.set_size_request(360 if field != 'name' else 510,50)
        entry.set_max_length(48 if field == 'name' else 15 if field == 'host' else 5)
        entry.set_text(initial)
        box.pack_start(entry,False,False,0)
        grid = gtk.Grid(column_spacing=5,row_spacing=5)
        rows = ['1234567890','qwertyuiop','asdfghjkl','zxcvbnm-_'] if field == 'name' else ['123','456','789','.0']
        def insert(widget, value):
            bounds = entry.get_selection_bounds()
            start,end = bounds[-2:] if bounds else (entry.get_position(),entry.get_position())
            current = entry.get_text()
            entry.set_text((current[:start]+value+current[end:])[:entry.get_max_length()])
            entry.set_position(start+len(value))
        def backspace(*unused):
            bounds = entry.get_selection_bounds()
            start,end = bounds[-2:] if bounds else (max(0,entry.get_position()-1),entry.get_position())
            current = entry.get_text()
            entry.set_text(current[:start]+current[end:])
            entry.set_position(start)
        for y,row in enumerate(rows):
            for x,char in enumerate(row):
                button = gtk.Button(label=char)
                button.set_size_request(47 if field == 'name' else 110,48)
                button.set_can_focus(False)
                button.connect('clicked',insert,char)
                if field == 'port' and char == '.':
                    button.set_sensitive(False)
                grid.attach(button,x,y,1,1)
        box.pack_start(grid,False,False,0)
        edits = gtk.Box(spacing=8)
        for label,callback in [('退格',backspace),
                               ('清空',lambda *_:entry.set_text(''))]:
            button = gtk.Button(label=label)
            button.set_size_request(120,48)
            button.set_can_focus(False)
            button.connect('clicked',callback)
            edits.pack_start(button,True,True,0)
        box.pack_start(edits,False,False,0)
        for label,response in [('取消',gtk.ResponseType.CANCEL),(accept,gtk.ResponseType.OK)]:
            dialog.add_button(label,response).set_size_request(150,52)
        dialog.show_all()
        response = dialog.run()
        value = entry.get_text().strip() if response == gtk.ResponseType.OK else None
        dialog.destroy()
        return value

    def choose_dialog(self, title, rows):
        gtk = self.Gtk
        if not rows:
            raise ValueError('当前没有可选择的对象')
        dialog = gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.set_decorated(False)
        dialog.set_border_width(14)
        box = dialog.get_content_area()
        box.set_spacing(8)
        box.pack_start(gtk.Label(label=title),False,False,0)
        scroll = gtk.ScrolledWindow()
        scroll.set_size_request(470,270)
        scroll.set_policy(gtk.PolicyType.NEVER,gtk.PolicyType.AUTOMATIC)
        items = gtk.Box(orientation=gtk.Orientation.VERTICAL,spacing=8)
        selected = []
        def choose(widget,value):
            selected.append(value)
            dialog.response(gtk.ResponseType.OK)
        for title,value in rows:
            button = gtk.Button(label=title)
            button.set_size_request(440,56)
            button.connect('clicked',choose,value)
            items.pack_start(button,False,False,0)
        scroll.add(items)
        box.pack_start(scroll,True,True,0)
        dialog.add_button('返回',gtk.ResponseType.CANCEL).set_size_request(150,52)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        return selected[0] if response == gtk.ResponseType.OK and selected else None

    def service_dialog(self, action):
        from board.interaction.ui_contract import validate_action
        view = self.services.read()
        snapshot = view['snapshot']
        if not snapshot or not snapshot['capabilities'].get(action):
            raise ValueError('该功能尚未接入')
        modules = snapshot['modules']
        params = None
        if action == 'target_select':
            selected = self.choose_dialog('选择当前对象',[(row['label'],row['key'])
                                            for row in modules.get('target',{}).get('tracks',[])])
            if selected:
                params = {'target':selected}
        elif action == 'identity_enroll':
            target = modules.get('target',{}).get('selected')
            if not target:
                raise ValueError('请先选择一个当前对象')
            name = self.keyboard_dialog('登记当前对象：输入姓名或拼音',field='name',accept='确认登记')
            if name is not None:
                params = {'target':target,'display_name':name,'confirmed':True}
        elif action == 'identity_delete':
            identity = modules.get('identity',{})
            row = self.choose_dialog('选择要删除的身份',[(r['display_name'],r) for r in identity.get('people',[])])
            if row:
                confirm = self.Gtk.MessageDialog(transient_for=self.window,modal=True,
                    message_type=self.Gtk.MessageType.QUESTION,buttons=self.Gtk.ButtonsType.NONE,
                    text='确认删除“'+row['display_name']+'”？')
                confirm.set_decorated(False)
                for label,response in [('返回',self.Gtk.ResponseType.CANCEL),('确认删除',self.Gtk.ResponseType.OK)]:
                    confirm.add_button(label,response).set_size_request(160,56)
                result = confirm.run()
                confirm.destroy()
                if result == self.Gtk.ResponseType.OK:
                    params = {'person_id':row['person_id'],'db_version':identity['db_version'],'confirmed':True}
        if params is None:
            return {'ok':True,'message':'已返回'}
        # A nested dialog may stay open across a track/database/connection change.
        validate_action(action,params,self.services.read()['snapshot'])
        return self.services.submit(action,params)

    def refresh_runtime(self, state, settings_text):
        from board.interaction.ui_contract import STATE_TEXT, display_state
        view = self.services.read()
        snapshot = view['snapshot']
        modules = snapshot['modules'] if snapshot else {}
        fixture = bool(snapshot and snapshot['source_kind'] == 'fixture')
        caps = snapshot['capabilities'] if snapshot else {}
        interaction = modules.get('interaction',{})
        audio = modules.get('audio',{})
        local_busy = state['phase'] != 'IDLE' or state['playing'] or state['paused']
        remote_busy = (audio.get('state') in ('RECORDING','PLAYING')
                       or interaction.get('state') in ('LISTENING','PROCESSING','SPEAKING'))
        link_text = {'DISABLED':'尚未启用连接','CONNECTING':'正在连接服务…',
                     'OFFLINE':'服务未连接，请检查地址与服务状态','STALE':'服务状态已过期，操作已暂停',
                     'READY':'服务已连接'}.get(view['link'],'服务待接入')
        self.mode_label.set_text('测试服务 · 数据仅用于联调' if fixture else
                                '服务已连接 · 按当前能力开放操作' if snapshot else '本地演示可用 · 语音与视觉待接入')
        status = STATE_TEXT.get(interaction.get('state'),'语音与视觉待接入')
        if local_busy:
            status = '正在播放本地演示' if not state['paused'] else '本地演示已暂停'
        self.status.set_text(status)
        target,identity = modules.get('target',{}), modules.get('identity',{})
        people = modules.get('vision',{}).get('people_count')
        self.target_label.set_text(('人数：'+str(people) if people is not None else '人数：—')+'  ·  目标：'+
            STATE_TEXT.get(target.get('state'),'待接入')+'  ·  身份：'+
            (identity.get('display_name') or display_state('identity',identity.get('state'))))
        self.target_label.set_line_wrap(False)
        self.target_label.set_ellipsize(3)
        self.transcript_label.set_text('你说：'+(interaction.get('transcript') or '—'))
        reply = interaction.get('reply') or ('本轮已取消。' if interaction.get('state') == 'CANCELLED' else
                    '接入语音服务后，在这里显示识别内容和回答。\n本地声音可在“演示”页试听。')
        if reply != self.reply_text:
            self.reply_view.get_buffer().set_text(reply)
            self.reply_text = reply
        timings = interaction.get('timings_ms',{})
        self.latency_label.set_text(' · '.join(label+' '+(str(round(timings[key]))+'ms' if key in timings else '—')
            for key,label in [('first_audio','首声'),('asr','ASR'),('vlm','VLM'),('tts','TTS')]))
        recording = audio.get('state') == 'RECORDING'
        self.record_button.set_label('停止录音' if recording else '开始录音')
        self.record_button.set_sensitive(bool(caps.get('record_stop' if recording else 'record_start'))
                                         and not local_busy and not view['pending_count'] and (recording or not remote_busy))
        self.record_button.set_tooltip_text('点击开始，再次点击停止' if caps.get('record_start') else '录音服务尚未接入')
        preview_ref = snapshot.get('preview') if snapshot else None
        frame_fresh = bool(preview_ref and time.monotonic()*1000-preview_ref['captured_mono_ms'] <= 1500)
        self.ask_button.set_sensitive(bool(caps.get('ask_frame')) and frame_fresh and not local_busy
                                      and not remote_busy and not view['pending_count'])
        self.ask_button.set_tooltip_text('使用当前画面发起问答' if caps.get('ask_frame') else '当前图问答尚未接入')
        for name in ('target_select','identity_enroll','identity_delete'):
            self.controls[name].set_sensitive(bool(caps.get(name)) and not view['pending_count'])
            self.controls[name].set_tooltip_text('操作由身份与目标服务确认' if caps.get(name) else '功能尚未接入')
        for index in range(len(self.lines)):
            self.controls['demo_'+str(index)].set_sensitive(not remote_busy)
        image = view['preview']
        if image and preview_ref != self.last_preview_key:
            try:
                with self.Image.open(io.BytesIO(image)) as source:
                    if source.width > 1920 or source.height > 1080:
                        raise ValueError('预览尺寸过大')
                    frame = source.convert('RGB')
                    frame.thumbnail((self.touch_layout['page']['width'],self.touch_layout['main']['preview']['height']),self.LANCZOS)
                pixbuf = self.Pixbuf.Pixbuf.new_from_bytes(self.GLib.Bytes.new(frame.tobytes()),
                    self.Pixbuf.Colorspace.RGB,False,8,frame.width,frame.height,frame.width*3)
                self.preview_image.set_from_pixbuf(pixbuf)
                self.last_preview_key = dict(preview_ref)
            except Exception:
                image = None
        if not image:
            self.preview_image.clear()
            self.last_preview_key = None
        self.preview_placeholder.set_visible(not bool(image))
        self.preview_placeholder.set_text('当前画面已失联或过期' if modules.get('camera',{}).get('state') == 'LOST' else
            '等待视觉画面\n接入后显示当前画面与目标')
        values = {key:(display_state(key,modules.get(key,{}).get('state')), modules.get(key,{}).get('state'))
                  for key in ('camera','vision','target','identity','motion','host','audio')}
        if not modules.get('camera') and self.device_inventory['camera_present']:
            values['camera'] = ('已枚举','UNKNOWN')
        if not audio and state['ui_settings']['available']:
            values['audio'] = ('音响就绪','READY')
        values['touch'] = ('已连接','READY') if self.touch_inputs else ('未检测到','UNKNOWN')
        lan = self.device_inventory['lan']
        values['network'] = ('已连接','READY') if lan is True else ('网线未连接','OFFLINE') if lan is False else ('未检测到','UNKNOWN')
        for key,(value,status_code) in values.items():
            label = self.device_cards[key]
            label.set_text(value)
            label.set_tooltip_text(modules.get(key,{}).get('detail') or value)
            style = label.get_style_context()
            for name in ('good','warn','bad','unknown'):
                style.remove_class(name)
            style.add_class('bad' if status_code in ('ERROR','FAULT','FAILED','LOST') else
                            'good' if status_code in ('READY','KNOWN','CONFIRMED') else
                            'unknown' if status_code == 'UNKNOWN' else 'warn')
        self.device_note.set_text(('测试数据 · ' if fixture else '')+link_text)
        self.connection_label.set_text(link_text+(' · 配置文件需要修复' if self.connection_store.error else ''))
        self.connection_label.set_tooltip_text(view['error'] or self.connection_store.error or link_text)
        self.host_status_label.set_text('语音主机：'+values['host'][0])
        if view['results']:
            result = view['results'][-1]
            if result['command_id'] != self.last_service_result:
                self.last_service_result = result['command_id']
                self.toast = ('请求已受理，等待服务状态更新' if result.get('accepted') else
                              '操作结果待确认' if result.get('outcome') == 'UNKNOWN' else '请求未被接受')
                self.toast_until = time.monotonic()+3
        recent = [row['interval_ms'] for row in list(self.samples)[-8:] if row['interval_ms']]
        fps = round(1000/(sum(recent)/len(recent)),1) if recent else 0
        footer = ('相机 '+values['camera'][0]+'   DPU '+STATE_TEXT.get(modules.get('npu',{}).get('state'),'待接入')+
                  '   PL '+STATE_TEXT.get(modules.get('pl',{}).get('state'),'待接入')+'   '+settings_text+'   LAN '+values['network'][0]+
                  '   保存 本地   隐私 待接入   模式 '+('测试' if fixture else '接入' if snapshot else '本地')+'   屏幕 '+str(fps)+'fps')
        self.footer.set_text(self.toast if time.monotonic() < self.toast_until else footer)
        self.runtime_view = {k:v for k,v in view.items() if k != 'preview'}
        self.runtime_view.update(protocol_version='aura-ui-1',frame_visible=bool(image),
                                 frame_reference=preview_ref if image else None)
        state.update(ui_runtime=self.runtime_view,ui_pages=list(self.page_names))

    def volume_changed(self, scale):
        if not self.updating_volume:
            self.mixer.request({'volume':max(0,min(100,round(scale.get_value())))})

    def apply_settings(self, values):
        from tools.board_ui_settings import validate
        values = validate(values)
        audio = {k:v for k,v in values.items() if k in ('volume','muted')}
        ui = {k:v for k,v in values.items() if k in ('fullscreen','economy')}
        if audio:
            self.mixer.request(audio)
        if ui:
            self.settings_store.update(ui)
            self.preferences.update(ui)
            if 'fullscreen' in ui:
                (self.window.fullscreen if ui['fullscreen'] else self.window.unfullscreen)()
                self.GLib.timeout_add(350,self.present_window)
            if 'economy' in ui:
                self.schedule_tick()
        return {'ok':True,'audio_pending':bool(audio)}

    def refresh_settings(self, state):
        from tools.board_ui_settings import touch_devices
        mix = self.mixer.read()
        now = time.monotonic()
        if now-self.last_touch_scan > 3:
            self.touch_inputs = touch_devices()
            self.device_inventory['camera_present'] = bool(list(Path('/sys/class/video4linux').glob('video*')))
            try:
                self.device_inventory['lan'] = Path('/sys/class/net/eth0/carrier').read_text().strip() == '1'
            except OSError:
                self.device_inventory['lan'] = None
            self.last_touch_scan = now
        if mix['pending']:
            text = '正在设置音量…'
        elif mix['available']:
            text = '音量 '+str(mix['volume'])+'%'+(' · 已静音' if mix['muted'] else '')
            if not self.volume_dragging:
                self.updating_volume = True
                self.volume_scale.set_value(mix['volume'])
                self.updating_volume = False
        else:
            text = mix['error'] or '读取音量…'
        self.volume_label.set_text(text)
        self.mute_button.set_label('取消静音' if mix['muted'] else '静音')
        self.fullscreen_button.set_label('退出全屏' if self.preferences['fullscreen'] else '进入全屏')
        self.economy_button.set_label('省电动画：'+('开' if self.preferences['economy'] else '关'))
        self.devices_label.set_text(('音响已连接' if mix['available'] else '音响不可用')+' · '+
                                   ('触摸已连接' if self.touch_inputs else '未检测到触摸设备'))
        self.pause_button.set_label('继续' if state['paused'] else '暂停')
        self.pause_button.set_sensitive(state['playing'] or state['paused'])
        self.cancel_button.set_sensitive(state['phase'] != 'IDLE' or state['playing'])
        state.update(ui_page=self.page,ui_settings=dict(mix,**{k:self.preferences[k] for k in ('fullscreen','economy')}),
                     touch_devices=self.touch_inputs)
        return text

    def key_pressed(self, widget, event):
        key = self.Gdk.keyval_name(event.keyval)
        if key == 'Escape':
            self.close()
            return True
        if key == 'space':
            self.native({'type':'pause'})
            return True
        return False

    def native(self, data):
        try:
            return self.command(data)
        except Exception as exc:
            return {'ok':False, 'error':str(exc)}

    def command(self, data):
        kind = data['type']
        if kind == 'ui_page':
            self.show_page(data['page'])
            return {'ok':True}
        if kind == 'ui_settings':
            return self.apply_settings(data['values'])
        if kind == 'ui_edit':
            field = data['field']
            entry = self.host_entry if field == 'host' else self.port_entry
            value = self.keyboard_dialog('输入服务 IPv4 地址' if field == 'host' else '输入服务端口',entry.get_text(),field)
            if value is not None:
                entry.set_text(value)
            return {'ok':True,'message':'输入完成，请保存连接设置' if value is not None else '已返回'}
        if kind in ('connection_apply','ui_service_config'):
            values = data.get('values') if kind == 'ui_service_config' else {
                'host':self.host_entry.get_text().strip(),'port':int(self.port_entry.get_text()),'enabled':data['enabled']}
            values = self.connection_store.update(values)
            self.services.configure(values)
            self.host_entry.set_text(values['host'])
            self.port_entry.set_text(str(values['port']))
            return {'ok':True,'message':'连接设置已保存，正在检测' if values['enabled'] else '连接已关闭'}
        if kind == 'ui_refresh':
            self.services.refresh()
            self.last_touch_scan = 0
            return {'ok':True,'message':'正在刷新状态'}
        if kind == 'service_dialog':
            return self.service_dialog(data['action'])
        if kind == 'record_toggle':
            snapshot = self.services.read()['snapshot']
            recording = snapshot and snapshot['modules'].get('audio',{}).get('state') == 'RECORDING'
            return self.command({'type':'service_action','action':'record_stop' if recording else 'record_start'})
        if kind == 'service_action':
            if data['action'] == 'cancel':
                return self.command({'type':'event','event':'cancel'})
            if data['action'] in ('record_start','ask_frame') and self.controller.public()['phase'] != 'IDLE':
                raise ValueError('请先停止本地演示')
            return self.services.submit(data['action'],data.get('params',{}))
        if kind == 'volume_step':
            self.volume_scale.set_value(max(0,min(100,round(self.volume_scale.get_value())+data['delta'])))
            return {'ok':True}
        if kind == 'toggle_setting':
            key = data['key']
            if key == 'muted':
                return self.apply_settings({key:not self.mixer.read()['muted']})
            if key in ('fullscreen','economy'):
                return self.apply_settings({key:not self.preferences[key]})
            raise ValueError('未知设置')
        if kind == 'restore_settings':
            from tools.board_ui_settings import DEFAULTS
            return self.apply_settings(DEFAULTS)
        if kind == 'demo':
            snapshot = self.services.read()['snapshot']
            modules = snapshot['modules'] if snapshot else {}
            if (modules.get('audio',{}).get('state') in ('RECORDING','PLAYING')
                    or modules.get('interaction',{}).get('state') in ('LISTENING','PROCESSING','SPEAKING')):
                raise ValueError('请先结束当前交互')
            index = data.get('index')
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(self.lines):
                raise ValueError('请选择有效台词')
            line = self.lines[index]
            job = self.controller.submit(line['text'], line['emotion'], line['action'])
            return {'ok':True, 'job':job}
        if kind == 'speak':
            # This entry only exposes the verified, selected demonstration cache.
            line = next((row for row in self.lines if row['text'] == data.get('text')), None)
            if line is None:
                raise ValueError('请先选择已有台词')
            return self.command({'type':'demo','index':self.lines.index(line)})
        if kind == 'pause':
            self.controller.toggle_pause()
        elif kind == 'event' and data.get('event') in ('cancel', 'reset'):
            self.controller.event(data['event'])
            try:
                return self.services.submit('cancel')
            except ValueError:
                self.services.cancel_local()
                return {'ok':True,'message':'本地已取消；远端状态待接入或确认'}
        elif kind in ('snapshot', 'save_evidence'):
            return self.save_evidence()
        else:
            raise ValueError('当前操作不可用')
        return {'ok':True}

    def tick(self):
        if self.closed:
            return False
        started = time.perf_counter()
        interval = None if self.last_tick is None else (started-self.last_tick)*1000
        self.last_tick = started
        try:
            for _ in range(16):
                try:
                    request = self.bridge.commands.get_nowait()
                except queue.Empty:
                    break
                if time.monotonic() > request['deadline']:
                    request['error'] = '操作已超时'
                else:
                    try:
                        request['result'] = self.command(request['data'])
                    except Exception as exc:
                        request['error'] = str(exc)
                request['done'].set()
            meta = self.controller.tick()
            if meta:
                color = self.tokens['colors']['panel_bg']
                background = self.Image.new('RGBA', meta['image'].size, color)
                background.alpha_composite(meta['image'])
                self.last_image = background.convert('RGB')
                scaled = self.last_image.resize((self.rect['w'], self.rect['h']), self.LANCZOS)
                self.current_pixbuf = self.Pixbuf.Pixbuf.new_from_bytes(self.GLib.Bytes.new(scaled.tobytes()),
                    self.Pixbuf.Colorspace.RGB, False, 8, scaled.width, scaled.height, scaled.width*3)
                self.portrait.set_from_pixbuf(self.current_pixbuf)
            state = self.controller.public()
            settings_text = self.refresh_settings(state)
            state.update(character=self.character, dialogue_enabled=False, backend='gtk3-gstreamer', cached_only=True)
            status = '已暂停' if state['paused'] else {'IDLE':'等你开口','VOICE_PREPARING':'正在准备声音…',
                'VOICE_STARTING':'正在准备播放…','SPEAKING':'正在说话','ACTION':'正在回应'}.get(state['phase'],state['phase'])
            self.demo_status.set_text('本地演示 · '+(state['error'] or status))
            self.reply.set_text(state['reply'])
            self.refresh_runtime(state,settings_text)
            self.samples.append({'t':state['visual_time'],'interval_ms':interval,
                'render_ms':(time.perf_counter()-started)*1000,**{key:state[key] for key in
                ('phase','state','asset','index','speech_gain','mouth_level','blink_active','playing','paused','audio_time')}})
            if self.last_image and (self.last_publish is None or started-self.last_publish >= .1):
                stream = io.BytesIO()
                self.last_image.save(stream, format='JPEG', quality=85)
                self.bridge.publish(state, stream.getvalue())
                self.last_publish = started
        except Exception as exc:
            message = type(exc).__name__+': '+str(exc)
            self.controller.last_error = message
            if not self.errors or self.errors[-1] != message:
                self.errors.append(message)
                print('STAGE ERROR '+message, flush=True)
            self.controller.cancel()
            self.status.set_text(message)
        return True

    def save_evidence(self):
        from tools.realtime_metrics import summarize
        stamp = str(time.time_ns())
        if self.last_image:
            self.last_image.save(self.evidence_root/('frame_'+stamp+'.png'))
        window = self.window.get_window()
        if window:
            allocation = self.window.get_allocation()
            screenshot = self.Gdk.pixbuf_get_from_window(window,0,0,allocation.width,allocation.height)
            if screenshot:
                screenshot.savev(str(self.evidence_root/('window_'+stamp+'.png')), 'png', [], [])
        rows = list(self.samples)
        controls = {}
        for name,control in self.controls.items():
            if control.get_mapped():
                rect = control.get_allocation()
                xy = control.translate_coordinates(self.fixed,0,0)
                controls[name] = {'x':xy[-2], 'y':xy[-1], 'width':rect.width, 'height':rect.height,
                                  'sensitive':control.get_sensitive()}
        dialogs = []
        for item in self.Gtk.Window.list_toplevels():
            if item != self.window and item.get_visible():
                rect = item.get_allocation()
                origin = item.get_window().get_origin()
                lengths = []
                def inspect_entries(widget):
                    if isinstance(widget,self.Gtk.Entry):
                        lengths.append(len(widget.get_text()))
                    if isinstance(widget,self.Gtk.Container):
                        for child in widget.get_children():inspect_entries(child)
                inspect_entries(item)
                dialogs.append({'title':item.get_title(),'width':rect.width,'height':rect.height,
                                'x':origin[-2],'y':origin[-1],'entry_lengths':lengths})
        report = {'backend':'gtk3-gstreamer','cached_only':True,'model_loaded':False,
            'font_sha256':self.font_hash,'source_hashes_at_launch':self.source_hashes,
            'config':self.config,'state':self.controller.public(),'stats':summarize(rows),
            'errors':self.errors,'samples':rows,'ui_settings':self.mixer.read(),
            'preferences':self.preferences,'ui_page':self.page,'touch_devices':self.touch_inputs,
            'input_events':list(self.input_events),
            'ui_runtime':self.runtime_view,'device_inventory':self.device_inventory,
            'ui_geometry':{'width':self.window.get_allocated_width(),'height':self.window.get_allocated_height(),
                           'visible_controls':controls,'dialogs':dialogs},
            'scope':'RUN_LOG_NOT_AUTOMATIC_ACOUSTIC_OR_FULL_SYSTEM_ACCEPTANCE'}
        path = self.evidence_root/('stage_'+stamp+'.json')
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (self.evidence_root/'latest_verification.json').write_text(json.dumps({k:v for k,v in report.items() if k!='samples'},
            ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return {'ok':True,'report':str(path),'stats':report['stats']}

    def cleanup(self):
        if self.services:
            self.services.close()
        if self.mixer:
            self.mixer.close()
        if self.output:
            self.output.close()
        if self.jobs:
            self.jobs.close()
        if self.bridge:
            self.bridge.close()

    def close(self):
        if self.closed:
            return True
        self.closed = True
        if self.timer:
            self.GLib.source_remove(self.timer)
        if self.foreground_timer:
            self.GLib.source_remove(self.foreground_timer)
        try:
            self.controller.cancel()
            self.save_evidence()
        finally:
            self.cleanup()
            self.window.destroy()
            self.Gtk.main_quit()
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--settings-file',type=Path)
    parser.add_argument('--check', action='store_true', help='Validate resources and libraries without opening a window or playing audio')
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    if config.get('schema_version') != 1 or config.get('backend') != 'gtk3-gstreamer':
        raise ValueError('Unsupported GTK stage configuration')
    if args.check:
        from tools.board_avatar_preflight import inspect_resources
        resources = inspect_resources(args.root)
        errors = list(resources['errors'])
        try:
            from tools.gstreamer_audio_worker import load_gst
            gst, unused = load_gst()
            load_gtk()
            import numpy
            from tools.pillow_compat import AFFINE, BICUBIC
            font = AURA/config['font_file']
            if not font.is_file():
                raise FileNotFoundError('Bundled Chinese font is missing')
            version = gst.version_string()
        except Exception as exc:
            errors.append({'component':'gtk_backend','error':type(exc).__name__+': '+str(exc)})
            version = None
        print(json.dumps({'status':'NOT_READY' if errors else 'PASS','resources':resources,'errors':errors,
                          'gstreamer':version,'device_opened':False,'window_opened':False},ensure_ascii=False))
        return 2 if errors else 0
    evidence = args.evidence_root or args.root.parent/'board_avatar_runs'/('gtk_'+str(time.time_ns()))
    stage = BoardAvatarStage(args.root, config, evidence, windowed=args.windowed,settings_file=args.settings_file)
    print('READY '+json.dumps({'backend':'gtk3-gstreamer','evidence':str(evidence),
                              'controls':'http://127.0.0.1:'+str(config['browser_port'])},ensure_ascii=False),flush=True)
    try:
        stage.Gtk.main()
    finally:
        if not stage.closed:
            stage.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
