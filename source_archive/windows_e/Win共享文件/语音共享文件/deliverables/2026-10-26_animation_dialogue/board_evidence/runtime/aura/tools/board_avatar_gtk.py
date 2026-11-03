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
import subprocess
import sys
import threading
import time

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
DEFAULT_ROOT = AURA.parent / 'deliverables/2026-10-06_xilan_live'
DEFAULT_CONFIG = AURA / 'config/board_avatar_gtk.json'


def create_runtime_core(factory):
    """Archival asset helpers may prepend an older runtime to sys.path."""
    search_path=list(sys.path)
    try:return factory('reuse')
    finally:sys.path[:]=search_path


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
        from tools.board_avatar_worker import AvatarRenderWorker
        from tools.board_recording import RecordingController
        from board.runtime.audio.transcription import TranscriptionJobs, TranscriptionStore
        from board.runtime.audio.conversation import ConversationJobs
        from tools.board_camera_preview import CameraPreviewWorker
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
                     'board_ui_settings.py', 'x11_foreground.py', 'board_screen_capture.py', 'board_avatar_worker.py',
                     'board_camera_preview.py', 'board_recording.py'):
            self.source_hashes['tools/' + name] = hashlib.sha256((AURA/'tools'/name).read_bytes()).hexdigest()
        reuse = AURA.parent/'deliverables/2026-10-06_avatar_reuse/preview_script.py'
        self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py'] = hashlib.sha256(reuse.read_bytes()).hexdigest()
        for name in ('ui_contract.py', 'ui_services.py'):
            rel = 'board/interaction/'+name
            self.source_hashes[rel] = hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        for rel in ('ui/board_touch_layout.json','config/board_ui_services.json'):
            self.source_hashes[rel] = hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        for rel in ('board/runtime/audio/capture.py','host/model_service/protocol.py',
                    'board/runtime/audio/transcription.py','common/asr_wire.py',
                    'board/runtime/audio/conversation.py','common/voice_wire.py'):
            self.source_hashes[rel] = hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        self.config = config
        if config.get('streaming_conversation'):
            for rel in ('common/voice_channel.py','common/conversation_selection.py','common/conversation_store.py',
                        'board/runtime/audio/voice_channel.py','board/runtime/audio/channel_jobs.py',
                        'tools/streaming_controller.py','tools/gstreamer_persistent_engine.py'):
                self.source_hashes[rel]=hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        if config.get('automatic_turns'):
            if not config.get('streaming_conversation') or not config.get('persistent_audio'):
                raise ValueError('Automatic turns require streaming conversation and persistent audio')
            for rel in ('board/runtime/audio/automatic_capture.py','board/runtime/audio/vad.py'):
                self.source_hashes[rel]=hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        if config.get('handsfree_dialogue'):
            if not config.get('automatic_turns'):raise ValueError('Hands-free entry requires automatic turns')
            for rel in ('tools/handsfree_recording.py','board/runtime/audio/attention_gate.py','common/handsfree_entry.py','common/handsfree_settings.py','tools/x11_display_activity.py'):
                self.source_hashes[rel]=hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        if config.get('voice_barge_in'):
            for rel in ('tools/barge_in_recording.py','tools/barge_in_capture.py','board/runtime/audio/echo_cancel.py',
                        'tools/gstreamer_persistent_engine.py','tools/gstreamer_audio.py',
                        'tools/gstreamer_audio_worker.py','tools/realtime_audio.py'):
                self.source_hashes[rel]=hashlib.sha256((AURA/rel).read_bytes()).hexdigest()
        from tools.x11_display_activity import DisplayActivity
        self.display_activity=DisplayActivity()
        self.font_hash = register_font(AURA/config['font_file'])
        initialized = self.Gtk.init_check([])
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            raise RuntimeError('Cannot connect to the current X display')
        self.jobs = self.output = self.bridge = self.mixer = self.services = self.preview_output = self.transcriber = None
        self.native_pixels = self.native_video = None
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
        self.preview_times = deque(maxlen=120)
        self.preview_frame_count = 0
        self.last_avatar_sequence = 0
        self.last_runtime_refresh = 0.0
        self.displayed_frames = 0
        self.preview_dialog = self.large_preview = self.large_preview_note = None
        self.identity_face_dialog = None
        self.voice_face_preview_dismissed = False
        self.last_service_result = None
        self.toast, self.toast_until = '', 0
        self.closed = False
        self.errors, self.samples = [], deque(maxlen=10000)
        self.last_tick = self.last_publish = None
        self.last_image = self.current_pixbuf = None
        self.diagnostic_thread = self.diagnostic_result = self.diagnostic_job = None
        self.timer = self.foreground_timer = self.controller = None
        try:
            core = create_runtime_core(create_demo_core)
            from tools.board_avatar_affine import configure_board_rendering
            if config.get('native_avatar'):
                from tools.native_pixels import NativePixels
                from tools.native_video import NativeVideo
                library=AURA/'tools/libaura_pixels.so'
                self.native_pixels=NativePixels(library,self.tokens['colors']['panel_bg'],(self.rect['w'],self.rect['h']),threads=int(config.get('native_pixel_threads',2)))
                self.native_pixels.configure(core)
                self.native_video=NativeVideo(library,(self.rect['w'],self.rect['h']))
            else:configure_board_rendering(core,self.tokens['colors']['panel_bg'])
            core.MAX_CACHED_SEQUENCES = int(config['cache_sequences'])
            if config.get('native_avatar'):
                for name in ('IDLE','PRESENT','LISTENING','THINKING','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):
                    core.sequence(name);core.sop(name)
            self.jobs = SpeechJobs(self.root, VoiceWorker(self.root, cached_only=True))
            streaming=bool(config.get('streaming_conversation',False))
            persistent=bool(config.get('persistent_audio',False))
            if streaming and not persistent:raise ValueError('Streaming conversation requires persistent audio')
            self.output = GStreamerAudioOutput(self.evidence_root/'audio_worker.log', config['audio_device'],persistent=persistent,
                                               echo_reference=bool(config.get('voice_barge_in')))
            self.board_boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            self.transcription_store = TranscriptionStore(AURA.parent/'avatar_transcription_settings.json')
            conversation_store=TranscriptionStore(AURA.parent/'avatar_conversation_settings.json')
            if conversation_store.read()['enabled']:
                if streaming:
                    from board.runtime.audio.channel_jobs import ChannelConversationJobs
                    self.transcriber=ChannelConversationJobs(conversation_store.read(),self.board_boot_id,self.root/'cache',
                        conversation_path=Path.home()/'.local/share/aura/conversation_selection.json')
                else:self.transcriber=ConversationJobs(conversation_store.read(),self.board_boot_id,self.root/'cache')
            else:self.transcriber = TranscriptionJobs(self.transcription_store.read(),self.board_boot_id)
            controller_type=RealtimeController
            if streaming:
                from tools.streaming_controller import StreamingController
                controller_type=StreamingController
            recording_type=RecordingController;recording_options={'audio_frontend':config.get('audio_frontend')}
            if config.get('handsfree_dialogue'):
                if not hasattr(self.transcriber,'select_conversation'):raise ValueError('Hands-free entry needs persistent channel conversations')
                from tools.handsfree_recording import HandsFreeRecordingController
                from common.handsfree_settings import HandsFreeSettings
                recording_type=HandsFreeRecordingController
                if config.get('voice_barge_in'):
                    if not streaming or not persistent:raise ValueError('Voice interruption needs persistent streaming audio')
                    from tools.barge_in_recording import BargeInRecordingController
                    recording_type=BargeInRecordingController
                recording_options={'boot_id':self.board_boot_id,
                                   'audio_frontend':config.get('audio_frontend'),
                                   'early_listen':bool(config.get('early_listen',False)),
                                   'monitor_settings':HandsFreeSettings(Path.home()/'.local/share/aura/handsfree_dialogue.json'),
                                   'attention_provider':lambda:self.transcriber.identity_snapshot()
                                   if self.transcriber.identity_snapshot else None}
            self.controller = AvatarRenderWorker(recording_type(controller_type(core,self.jobs,self.output),transcriber=self.transcriber,**recording_options),
                self.tokens['colors']['panel_bg'],(self.rect['w'],self.rect['h']),
                .25 if self.preferences['economy'] else (1/24 if config.get('native_avatar') else config['tick_ms']/1000),native_video=self.native_video,visual_fps=config.get('stable_avatar_fps',8) if config.get('native_avatar') else None,performance_path=self.evidence_root/'render_performance.jsonl')
            self.mixer = MixerService(self.settings_store)
            defaults = json.loads((AURA/'config/board_ui_services.json').read_text(encoding='utf-8'))
            self.connection_store = ConnectionStore(AURA.parent/'avatar_service_settings.json', defaults['connection'])
            self.services = UiServiceClient(self.board_boot_id,self.connection_store.read(),poll_seconds=.1,local_raw=True)
            if hasattr(self.transcriber,'identity_snapshot'):
                self.transcriber.identity_snapshot=self.services.identity_snapshot
            self.preview_output = CameraPreviewWorker(self.services)
            self.bridge = StageBridge(self.root, int(config['browser_port']),
                                      extra_commands=('ui_settings', 'ui_page', 'ui_service_config',
                                                      'service_action', 'ui_refresh', 'preview_open', 'record_toggle', 'conversation_toggle', 'ui_layer', 'asr_config'))
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
        # Economy slows the avatar worker, never the camera or touch event loop.
        interval = int(self.config['tick_ms'])
        if self.controller:
            self.controller.set_interval(.25 if self.preferences['economy'] else (1/24 if self.config.get('native_avatar') else interval/1000))
        if self.config.get('native_avatar'):interval=max(100,min(200,int(self.config.get('native_ui_tick_ms',100))))
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
               'button.nav {font-size:17px;background-image:none;}'
               'button.nav:hover {background:#e9f2f6;}'
               'button.nav.selected, button.nav.selected:hover {background:'+colors['accent']+';}'
               'button.selected label, button.primary label {color:white;text-shadow:none;}'
               'button.primary:disabled label {color:#91969b;}'
               'button.quiet {background:transparent;border-color:transparent;box-shadow:none;color:#8b969b;font-size:17px;padding:0;}'
               'label.section {font-size:14px;color:'+colors['text_secondary']+';}'
               'label.insight_value {font-size:24px;color:'+colors['accent_dark']+';}'
               'label.vision_summary {font-size:18px;}'
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
        if (spec['schema_version'] != 'aura-touch-layout-2' or spec['canvas'] != self.layout['canvas']
                or spec['page']['width'] != left_width or spec['page']['x'] != pad
                or spec['page']['y']+spec['page']['height'] > self.layout['top_area']['y1']):
            raise ValueError('触屏页面与板端布局合同不一致')
        self.label('AURA · '+self.character, pad, 6, left_width, 32, 'title')
        self.mode_label = self.label('本地演示可用 · 语音与视觉待接入', pad, 36, left_width, 18)
        self.mode_label.get_style_context().add_class('muted')
        button_width = (left_width-12)//2
        names = [('main','玩偶交流'), ('vision','视觉追踪'), ('demo','声音测试'),
                 ('devices','设备状态'), ('connection','服务连接'), ('settings','设置')]
        self.page_names = [row[0] for row in names]
        if self.page_names != spec['pages']:
            raise ValueError('触屏页面清单不一致')
        nav = spec['navigation']
        self.ui_layer = 'presentation'
        self.last_presentation_page = 'main'
        self.navigation_panels = {}
        titles = dict(names)
        for layer, members in spec['layers'].items():
            panel = gtk.Fixed()
            panel.set_size_request(left_width,nav['height'])
            self.fixed.put(panel,pad,nav['y'])
            self.navigation_panels[layer] = panel
            tab_width = (left_width-(len(members)-1)*nav['gap'])//len(members)
            for index,name in enumerate(members):
                item = self.button(titles[name], {'type':'ui_page','page':name}, index*(tab_width+nav['gap']), 0,
                                   tab_width, nav['height'], parent=panel, key='page_'+name)
                item.get_style_context().add_class('nav')
        self.pages = gtk.Stack()
        self.pages.set_size_request(left_width, spec['page']['height'])
        self.fixed.put(self.pages, spec['page']['x'], spec['page']['y'])
        page_widgets = {name:gtk.Fixed() for name in self.page_names}
        for name,page in page_widgets.items():
            page.set_size_request(left_width,spec['page']['height'])
            self.pages.add_named(page,name)
        main, vision, demo, devices, connection, settings = [page_widgets[n] for n in self.page_names]
        slots = spec['main']
        self.status = self.label('等你开口', 0, slots['status']['y'], left_width, slots['status']['height'], 'status', main)
        self.label('正对汐蓝开口即可，说完后自动接话。' if self.config.get('handsfree_dialogue') else
                   '点一次开始对话，说完后自动接话。' if self.config.get('automatic_turns') else
                   '和汐蓝聊一聊，按下按钮开始说话。',0,slots['hint']['y'],left_width,slots['hint']['height'],parent=main).get_style_context().add_class('muted')
        self.label('你说',0,slots['transcript_title']['y'],left_width,slots['transcript_title']['height'],parent=main).get_style_context().add_class('section')
        self.label('汐蓝的回答',0,slots['reply_title']['y'],left_width,slots['reply_title']['height'],parent=main).get_style_context().add_class('section')
        video = spec['vision']
        self.preview_box = gtk.EventBox()
        self.preview_box.get_style_context().add_class('card')
        self.preview_box.set_size_request(left_width,video['preview']['height'])
        overlay = gtk.Overlay()
        self.preview_image = gtk.DrawingArea()
        self.preview_image.set_size_request(video['preview']['image_width'],video['preview']['image_height'])
        self.preview_image.set_halign(gtk.Align.CENTER)
        self.preview_image.connect('map',self.attach_preview,'vision',video['preview']['image_width'],video['preview']['image_height'])
        self.preview_image.connect('unmap',self.detach_preview,'vision')
        overlay.add(self.preview_image)
        self.preview_placeholder = gtk.Label(label='等待视觉画面\n接入后显示当前画面与目标')
        self.preview_placeholder.set_justify(gtk.Justification.CENTER)
        overlay.add_overlay(self.preview_placeholder)
        self.preview_box.add(overlay)
        vision.put(self.preview_box,0,video['preview']['y'])
        self.preview_expand = self.button('放大画面',{'type':'preview_open'},left_width-112,
            video['note']['y'],104,48,vision,'camera_expand')
        self.vision_note = self.label('画面中的人数、当前目标与身份显示在右侧。',0,video['note']['y'],left_width-124,video['note']['height'],parent=vision)
        self.vision_note.get_style_context().add_class('muted')
        transcript_scroll = gtk.ScrolledWindow()
        transcript_scroll.set_size_request(left_width,slots['transcript']['height'])
        transcript_scroll.set_policy(gtk.PolicyType.NEVER,gtk.PolicyType.AUTOMATIC)
        self.transcript_label = gtk.Label(label='等待你的声音…')
        self.transcript_label.set_xalign(0)
        self.transcript_label.set_yalign(0)
        self.transcript_label.set_line_wrap(True)
        self.transcript_label.set_max_width_chars(34)
        self.transcript_label.set_selectable(True)
        transcript_scroll.add(self.transcript_label)
        main.put(transcript_scroll,0,slots['transcript']['y'])
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
        third = (left_width-24)//3
        quarter = (left_width-36)//4
        action_y,action_h = slots['actions']['y'],slots['actions']['height']
        self.record_button = self.button('开始录音',{'type':'record_toggle'},0,action_y,button_width,action_h,main,'record')
        self.record_button.get_style_context().add_class('primary')
        self.ask_button = self.button('当前图问答',{'type':'service_action','action':'ask_frame'},quarter+12,
                                      video['actions']['y'],quarter,video['actions']['height'],vision,'ask_frame')
        self.button('选择目标',{'type':'service_dialog','action':'target_select'},0,
                    video['actions']['y'],quarter,video['actions']['height'],vision,'vision_target_select')
        self.button('身份管理',{'type':'service_dialog','action':'identity_manage'},2*(quarter+12),
                    video['actions']['y'],quarter,video['actions']['height'],vision,'vision_identity')
        self.button('设置',{'type':'ui_page','page':'settings'},3*(quarter+12),
                    video['actions']['y'],quarter,video['actions']['height'],vision,'vision_settings')
        self.interaction_cancel = self.button('取消本轮',{'type':'event','event':'cancel'},button_width+12,
                                               action_y,button_width,action_h,main,'interaction_cancel')
        self.interaction_cancel.get_style_context().add_class('danger')
        self.demo_status = self.label('本地缓存演示',0,0,left_width,34,'status',demo)
        self.reply = self.label('选择台词即可播放已保存的汐蓝声音。',0,40,left_width,74,parent=demo)
        self.latency_label = self.label('首声 — · ASR — · VLM — · TTS —',0,418,left_width,14,parent=connection)
        self.latency_label.get_style_context().add_class('muted')
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
        self.host_status_label = self.label('语音主机：待接入',0,394,left_width,24,parent=connection)
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
        self.button('个人记忆',{'type':'profile_dialog'},0,368,(left_width-8)//2,56,settings,'profile_dialog')
        self.button('恢复默认设置',{'type':'restore_settings'},(left_width+8)//2,368,(left_width-8)//2,56,settings,'restore_settings')
        panel = self.layout['right_panel']
        self.avatar_title = self.label(self.character, panel['x0']+panel['padding'], panel['y0']+panel['padding'],
                   panel['x1']-panel['x0']-2*panel['padding'], self.layout['right_inner']['label_h'], 'avatar_title')
        self.portrait = gtk.DrawingArea() if self.native_video else gtk.Image()
        if self.native_video:
            self.portrait.set_size_request(self.rect['w'],self.rect['h'])
            self.portrait.connect('map',self.attach_native_portrait)
        self.fixed.put(self.portrait, self.geometry['x']+self.rect['x'], self.geometry['y']+self.rect['y'])
        self.vision_insights = gtk.Fixed()
        self.vision_insights.set_size_request(self.geometry['w'],self.geometry['h'])
        self.fixed.put(self.vision_insights,self.geometry['x'],self.geometry['y'])
        insight_width = self.geometry['w']
        self.label('看见、选择，然后持续关注',12,8,insight_width-24,30,parent=self.vision_insights).get_style_context().add_class('muted')
        self.insight_labels = {}
        for key,title,y,h in (('people','画面中的人',56,76),('target','当前跟随目标',144,88),
                              ('identity','目标身份',244,76)):
            card = gtk.EventBox()
            card.get_style_context().add_class('card')
            card.set_size_request(insight_width,h)
            inner = gtk.Fixed()
            card.add(inner)
            self.label(title,14,6,insight_width-28,22,parent=inner).get_style_context().add_class('section')
            value = self.label('等待画面',14,30,insight_width-28,h-34,parent=inner)
            value.set_line_wrap(False)
            value.set_ellipsize(3)
            value.get_style_context().add_class('insight_value')
            self.insight_labels[key] = value
            self.vision_insights.put(card,0,y)
        self.label('画面解读',12,338,insight_width-24,26,parent=self.vision_insights).get_style_context().add_class('section')
        self.vision_summary = self.label('接入摄像头后，在这里了解当前画面。',12,374,insight_width-24,116,parent=self.vision_insights)
        self.vision_summary.set_max_width_chars(22)
        self.vision_summary.get_style_context().add_class('vision_summary')
        bar = self.layout['bottom_bar']
        self.footer = self.label('正在读取设备状态…', 8, bar['y0']+4, width-80, bar['height']-8,'footer')
        self.footer.set_line_wrap(False)
        self.footer.set_ellipsize(3)
        switch = spec['layer_switch']
        self.layer_button = self.button('···',{'type':'ui_layer'},switch['x'],switch['y'],switch['width'],switch['height'],key='layer_switch')
        self.layer_button.get_style_context().add_class('quiet')
        self.layer_button.set_tooltip_text('切换到调试层')
        self.window.show_all()
        self.show_page('main')
        if self.preferences['fullscreen']:
            self.window.fullscreen()

    def show_page(self, page):
        if page not in self.page_names:
            raise ValueError('未知页面')
        self.page = page
        if page in self.touch_layout['layers']['presentation']:
            self.ui_layer = 'presentation'
            self.last_presentation_page = page
        elif page in ('demo','devices','connection'):
            self.ui_layer = 'debug'
        self.pages.set_visible_child_name(page)
        for layer,panel in self.navigation_panels.items():
            panel.set_visible(layer == self.ui_layer)
        is_vision = page == 'vision'
        self.portrait.set_visible(not is_vision)
        self.vision_insights.set_visible(is_vision)
        self.avatar_title.set_text('视觉解读' if is_vision else self.character)
        self.layer_button.set_label('返回' if self.ui_layer == 'debug' else '···')
        self.layer_button.set_tooltip_text('返回演示层' if self.ui_layer == 'debug' else '切换到调试层')
        for name in self.page_names:
            style = self.controls['page_'+name].get_style_context()
            (style.add_class if page == name else style.remove_class)('selected')

    def show_layer(self, layer):
        if layer not in self.touch_layout['layers']:
            raise ValueError('未知界面层')
        self.ui_layer = layer
        self.show_page(self.last_presentation_page if layer == 'presentation' else 'devices')

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
        if action == 'identity_manage':
            rows = [('登记人脸', 'identity_enroll'), ('删除已登记身份', 'identity_delete')]
            rows = [(label, name) for label, name in rows if snapshot and
                    (snapshot['modules'].get('identity') if name=='identity_enroll' else snapshot['capabilities'].get(name))]
            if not rows:
                raise ValueError('请先选择对象并正对摄像头，等待清晰人脸')
            selected = self.choose_dialog('身份管理', rows)
            return self.service_dialog(selected) if selected else {'ok': True, 'message': '已返回'}
        if not snapshot or (not snapshot['capabilities'].get(action) and
                           not (action=='identity_enroll' and snapshot['modules'].get('identity'))):
            raise ValueError('该功能尚未接入')
        modules = snapshot['modules']
        params = None
        if action == 'target_select':
            selected = self.choose_dialog('选择当前对象',[(row['label'],row['key'])
                                            for row in modules.get('target',{}).get('tracks',[])])
            if selected:
                params = {'target':selected}
        elif action == 'identity_enroll':
            if modules.get('identity',{}).get('enrollment_sampling') is not None:
                identity=modules['identity'];target=identity.get('face_target')
                if not target:raise ValueError('请先正对镜头，等待清晰人脸')
                name=self.keyboard_dialog('登记人脸：输入称呼',field='name',accept='继续')
                if name is None:return {'ok':True,'message':'已返回'}
                name=name.strip()
                if not name:raise ValueError('请输入有效称呼')
                existing=next((r for r in identity['people'] if r['display_name'].casefold()==name.casefold()),None)
                replace_id=existing['person_id'] if existing else ''
                enrollment_target=self.run_identity_face_dialog(name,target,replace_id=replace_id)
                if not enrollment_target:return {'ok':True,'message':'已返回'}
                params={'target':enrollment_target,'display_name':name,'confirmed':True}
                if replace_id:params.update(replace_person_id=replace_id,db_version=identity['db_version'])
                validate_action(action,params,self.services.read()['snapshot'])
                return self.services.submit(action,params)
            target=self.run_identity_face_dialog()
            if not target:return {'ok':True,'message':'已返回'}
            snapshot=self.services.read()['snapshot']
            identity=snapshot['modules'].get('identity',{}) if snapshot else {}
            selected=(identity.get('face_target') if identity.get('target_kind')=='face' else
                      snapshot['modules'].get('target',{}).get('selected')) if snapshot else None
            if target!=selected:raise ValueError('人脸对象已变化，请重新登记')
            name = self.keyboard_dialog('登记人脸：输入称呼',field='name',accept='继续')
            if name is not None:
                if self.run_identity_face_dialog(name.strip(),target):
                    params = {'target':target,'display_name':name.strip(),'confirmed':True}
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

    def create_identity_face_dialog(self, *, voice=False, name=None, target=None, replace_id=''):
        gtk=self.Gtk
        dialog=gtk.Dialog(title='语音登记人脸' if voice else '确认登记人脸' if name else '登记人脸',
                          transient_for=self.window,modal=not voice)
        dialog.set_decorated(False);dialog.set_default_size(440,480)
        content=dialog.get_content_area();content.set_spacing(12)
        content.set_margin_top(18);content.set_margin_bottom(12)
        content.set_margin_start(20);content.set_margin_end(20)
        title=gtk.Label(label='请正对摄像头' if not name else ('更新已有身份：' if replace_id else '登记称呼：')+name)
        content.pack_start(title,False,False,0)
        frame=gtk.Frame(label='登记人脸');frame.set_halign(gtk.Align.CENTER)
        image=gtk.Image();image.set_size_request(264,264);frame.add(image)
        content.pack_start(frame,False,False,0)
        note=gtk.Label(label='等待清晰人脸…');note.set_line_wrap(True);note.set_max_width_chars(28)
        content.pack_start(note,False,False,0)
        content.pack_start(gtk.Label(label='仅显示人脸 · 预览不保存照片'),False,False,0)
        dialog.add_button('收起预览' if voice else '返回',gtk.ResponseType.CANCEL).set_size_request(150,52)
        button=None
        retry=None
        if not voice:
            retry=dialog.add_button('重新采样',gtk.ResponseType.APPLY);retry.set_sensitive(False)
            button=dialog.add_button('确认更新登记' if replace_id else '确认登记' if name else '继续填写称呼',gtk.ResponseType.OK)
            button.set_size_request(180,52);button.set_sensitive(False)
        self.identity_face_dialog={'dialog':dialog,'image':image,'note':note,'button':button,
                                   'voice':voice,'target':target,'key':None,'display_target':None,'sampling_started':False,
                                   'replace_id':replace_id,'retry':retry,'sampling_id':None}
        if voice:
            def dismiss(*_):
                self.voice_face_preview_dismissed=True;self.close_identity_face_dialog()
            dialog.connect('response',dismiss)
        self.services.set_identity_preview(True)
        dialog.show_all();self.refresh_identity_face_dialog()
        return dialog

    def close_identity_face_dialog(self):
        value=self.identity_face_dialog;self.identity_face_dialog=None
        if value:value['dialog'].destroy()
        if self.services:self.services.set_identity_preview(False)

    def run_identity_face_dialog(self, name=None, target=None, *, replace_id=''):
        if self.identity_face_dialog:raise ValueError('请先完成当前语音登记')
        dialog=self.create_identity_face_dialog(name=name,target=target,replace_id=replace_id)
        completed=False
        try:
            response=dialog.run();panel=self.identity_face_dialog
            while response==self.Gtk.ResponseType.APPLY and panel:
                view=self.services.read();state=view.get('snapshot')
                if state and state['capabilities'].get('identity_sample_start'):
                    params={'target':panel['target'] or panel['display_target']}
                    if replace_id:params.update(replace_person_id=replace_id,db_version=state['modules']['identity']['db_version'])
                    self.services.submit('identity_sample_start',params)
                response=dialog.run();panel=self.identity_face_dialog
            if (response==self.Gtk.ResponseType.OK and panel and panel['button'].get_sensitive()
                    and panel['display_target']):
                completed=True;return dict(panel['display_target'])
            return None
        finally:
            if not completed:
                view=self.services.read();state=view.get('snapshot')
                sample=state['modules'].get('identity',{}).get('enrollment_sampling') if state else None
                if sample and sample['session_id'] and state['capabilities'].get('identity_sample_cancel'):
                    self.services.submit('identity_sample_cancel',{'session_id':sample['session_id']})
            self.close_identity_face_dialog()

    def refresh_identity_face_dialog(self):
        panel=self.identity_face_dialog
        if not panel:return
        view=self.services.read();snapshot=view['snapshot']
        identity=snapshot['modules'].get('identity',{}) if snapshot else {}
        selected=(identity.get('face_target') if identity.get('target_kind')=='face' else
                  snapshot['modules'].get('target',{}).get('selected')) if snapshot else None
        ref=view.get('identity_face_reference');raw=view.get('identity_face')
        usable=bool(raw and ref and (panel['target'] is None or panel['target']==selected))
        key=repr(ref) if usable else None
        if key!=panel['key']:
            panel['image'].clear();panel['key']=None;panel['display_target']=None
            if usable:
                try:
                    loader=self.Pixbuf.PixbufLoader.new_with_type('png');loader.write(raw);loader.close()
                    pixbuf=loader.get_pixbuf()
                    if (pixbuf.get_width(),pixbuf.get_height())!=(112,112):raise ValueError('人脸尺寸不正确')
                    panel['image'].set_from_pixbuf(pixbuf.scale_simple(264,264,self.Pixbuf.InterpType.BILINEAR))
                    panel['key']=key
                    panel['display_target']=dict(ref['target'])
                except Exception:usable=False
        usable=usable and panel['key'] is not None
        note='当前人脸清晰，可继续登记' if usable else identity.get('detail') or '等待相机与清晰正面人脸'
        sampling=identity.get('enrollment_sampling')
        if sampling:
            if (panel['sampling_id'] is None and sampling.get('session_id')
                    and (sampling.get('bound_target')==panel['target'] or panel['voice'] and panel['target'] is None)):
                panel['sampling_id']=sampling['session_id']
            if (sampling.get('bound_target')==selected and selected is not None
                    and sampling.get('session_id')==panel['sampling_id'] and sampling['stage'] not in ('idle','failed')):
                panel['target']=dict(selected)
            if (not panel['voice'] and not panel['sampling_started']
                    and usable and snapshot['capabilities'].get('identity_sample_start') and not view['pending_count']):
                panel['sampling_started']=True
                params={'target':selected}
                if panel['replace_id']:params.update(replace_person_id=panel['replace_id'],db_version=identity['db_version'])
                self.services.submit('identity_sample_start',params)
            if sampling['stage']!='idle':
                counts=sampling['counts']
                progress=('自动选样 {collect}/10 · 验证 {validate}/5' if 'collect' in counts else
                          '正脸 {front}/4 · 左 {left}/3 · 右 {right}/3 · 验证 {validate}/5')
                note=sampling['detail']+'\n'+progress.format(**counts)
                if sampling['stage']=='ready' and not snapshot['capabilities'].get('identity_enroll'):
                    note='选样已保留，请看向镜头，等待当前人脸验证\n'+progress.format(**counts)
        if panel['retry']:panel['retry'].set_sensitive(bool(sampling and sampling['stage']=='failed'
            and usable and snapshot['capabilities'].get('identity_sample_start') and not view['pending_count']))
        if usable and identity.get('state')=='KNOWN':note='当前人脸已登记：'+identity.get('display_name','')
        if panel['target'] is not None and selected is not None and selected!=panel['target']:
            note='对象已变化，请返回后重新登记'
        panel['note'].set_text(note)
        if panel['button']:
            panel['button'].set_sensitive(bool(usable and snapshot['capabilities'].get('identity_enroll') and not view['pending_count']))

    def refresh_voice_face_dialog(self, transcription):
        active=transcription.get('service',{}).get('voice_enrollment',{}).get('active',False)
        if not active:
            self.voice_face_preview_dismissed=False
            if self.identity_face_dialog and self.identity_face_dialog['voice']:self.close_identity_face_dialog()
        elif not self.identity_face_dialog and not self.voice_face_preview_dismissed:
            self.create_identity_face_dialog(voice=True)
        self.refresh_identity_face_dialog()

    def open_preview(self):
        if self.preview_dialog:
            self.preview_dialog.present()
            return {'ok':True}
        dialog = self.Gtk.Dialog(title='摄像头实时画面',transient_for=self.window,modal=True)
        dialog.set_decorated(False)
        dialog.set_resizable(False)
        dialog.set_default_size(960,550)
        dialog.set_position(self.Gtk.WindowPosition.CENTER_ON_PARENT)
        content = dialog.get_content_area()
        content.set_spacing(4)
        content.set_border_width(8)
        content.pack_start(self.Gtk.Label(label='摄像头实时画面'),False,False,0)
        self.large_preview = self.Gtk.DrawingArea()
        self.large_preview.set_size_request(587,440)
        self.large_preview.set_halign(self.Gtk.Align.CENTER)
        self.large_preview.connect('map',self.attach_preview,'large',587,440)
        self.large_preview.connect('unmap',self.detach_preview,'large')
        content.pack_start(self.large_preview,True,True,0)
        self.large_preview_note = self.Gtk.Label(label='等待当前画面…')
        content.pack_start(self.large_preview_note,False,False,0)
        dialog.add_button('返回',self.Gtk.ResponseType.CLOSE).set_size_request(120,48)
        def dismissed(*_):
            self.detach_preview(self.large_preview,'large')
            self.preview_dialog = self.large_preview = self.large_preview_note = None
            dialog.destroy()
        dialog.connect('response',dismissed)
        dialog.connect('delete-event',lambda *_:(dismissed() or True))
        self.preview_dialog = dialog
        self.last_preview_key = None
        dialog.show_all()
        return {'ok':True}

    def attach_native_portrait(self,area):
        import gi
        gi.require_version('GdkX11','3.0')
        from gi.repository import GdkX11
        handle=GdkX11.X11Window.get_xid(area.get_window())
        self.Gdk.Display.get_default().sync()
        self.native_video.attach(handle)

    def attach_preview(self, area, name, width, height):
        if not self.preview_output:return
        import gi
        gi.require_version('GdkX11','3.0')
        from gi.repository import GdkX11
        handle=GdkX11.X11Window.get_xid(area.get_window())
        generations=getattr(self,'preview_map_generations',{})
        generation=generations.get(name,0)+1
        generations[name]=generation;self.preview_map_generations=generations
        # get_xid promotes the drawing area to a native X11 window. Allow GTK
        # to commit its allocation before ximagesink caches the window size.
        def bind():
            if self.preview_map_generations.get(name)!=generation:return False
            if not self.preview_output:return False
            if not area.get_realized() or not area.get_mapped():return False
            self.Gdk.Display.get_default().sync()
            bindings=getattr(self,'preview_bindings',{})
            binding=(handle,width,height)
            # A remapped XID can match the old value while ximagesink still
            # retains the old drawable state. Rebind once per map event.
            self.preview_output.attach(name,handle,width,height)
            bindings[name]=binding
            self.preview_bindings=bindings
            return False
        self.GLib.timeout_add(50,bind)

    def detach_preview(self, area, name):
        generations=getattr(self,'preview_map_generations',{})
        generations[name]=generations.get(name,0)+1
        self.preview_map_generations=generations
        if self.preview_output:self.preview_output.detach(name)
        getattr(self,'preview_bindings',{}).pop(name,None)

    def refresh_runtime(self, state, settings_text):
        from board.interaction.ui_contract import STATE_TEXT, display_state
        view = self.services.read()
        snapshot = view['snapshot']
        display=self.preview_output.read('vision') if self.preview_output else {'frame_visible':False,'frame_reference':None}
        modules = snapshot['modules'] if snapshot else {}
        fixture = bool(snapshot and snapshot['source_kind'] == 'fixture')
        caps = snapshot['capabilities'] if snapshot else {}
        interaction = modules.get('interaction',{})
        audio = modules.get('audio',{})
        local_recording = state.get('local_recording',{})
        automatic = state.get('automatic_conversation',{})
        handsfree=state.get('handsfree_dialogue',{})
        self.display_activity.tick(bool(handsfree.get('enabled') and handsfree.get('visual_bound')
                                       or automatic.get('enabled') or state.get('playing')))
        transcription = state.get('local_transcription',{})
        self.refresh_voice_face_dialog(transcription)
        local_conversation=bool(transcription.get('service',{}).get('conversation'))
        local_recording_active = local_recording.get('state') == 'RECORDING'
        local_busy = state['phase'] != 'IDLE' or state['playing'] or state['paused']
        remote_busy = (audio.get('state') in ('RECORDING','PLAYING')
                       or interaction.get('state') in ('LISTENING','PROCESSING','SPEAKING'))
        link_text = {'DISABLED':'尚未启用连接','CONNECTING':'正在连接服务…',
                     'OFFLINE':'服务未连接，请检查地址与服务状态','STALE':'服务状态已过期，操作已暂停',
                     'READY':'服务已连接'}.get(view['link'],'服务待接入')
        camera_only = bool(modules.get('camera') and not modules.get('interaction'))
        self.mode_label.set_text('测试服务 · 数据仅用于联调' if fixture else
                                ('相机与身份已接入 · 语音使用独立服务' if modules.get('identity') else
                                 '相机已接入 · 语音与身份待接入') if camera_only else
                                '服务已连接 · 按当前能力开放操作' if snapshot else '本地演示可用 · 语音与视觉待接入')
        status = STATE_TEXT.get(interaction.get('state'),
            '录音可用 · 等你开口' if local_recording.get('can_start') else '等待语音服务')
        if local_busy:
            status = '正在播放本地演示' if not state['paused'] else '本地演示已暂停'
        if local_recording_active:
            status = '正在录音 · '+str(round(local_recording['duration_seconds'],1))+' 秒'
        elif not local_busy and local_recording.get('state') == 'READY':
            status = '录音已完成 · '+str(round(local_recording['result']['duration_seconds'],2))+' 秒'
        elif not local_busy and local_recording.get('error'):
            status = '录音失败：'+local_recording['error']
        if not local_recording_active and transcription.get('state') == 'TRANSCRIBING':
            status = '正在听懂并准备回答…' if transcription.get('service',{}).get('conversation') else '录音已完成 · 正在转写…'
        elif not local_recording_active and transcription.get('state') == 'READY':
            status = '转写完成 · '+str(round(transcription.get('recognition_ms',0)))+' ms'
        elif transcription.get('state') == 'EMPTY':
            status = '未识别到内容，请重新录音'
        elif transcription.get('state') == 'ERROR':
            status = '转写失败，请检查识别服务连接'
        if transcription.get('voice_reply'):
            status='汐蓝正在说话…' if state['playing'] else '本轮回答已暂停' if state['paused'] else '汐蓝已回答'
        if transcription.get('service',{}).get('streaming'):
            status=('汐蓝正在想一想…' if state.get('phase')=='THINKING_FEEDBACK' else
                    '汐蓝正在说话…' if state.get('phase')=='SPEAKING' else
                    '正在认真想，想好就告诉你…' if state.get('phase')=='THINKING' else
                    '汐蓝已回答' if transcription.get('state')=='ANSWERED' else status)
        if not fixture and self.ui_layer == 'presentation':
            self.mode_label.set_text('视觉追踪 · '+('相机已连接' if modules.get('camera',{}).get('state') == 'READY' else '等待相机连接')
                if self.page == 'vision' else '玩偶交流 · 连续对话' if self.config.get('automatic_turns') else '玩偶交流 · 录音后自动回答' if local_conversation else
                '玩偶交流 · '+('语音主机已连接' if modules.get('host',{}).get('state') == 'READY' else '语音主机待连接'))
        if automatic.get('enabled'):
            if automatic.get('state') == 'LISTENING':
                status = '正在听你说…' if automatic.get('speech_active') else '我在听，停顿后自动回答'
            elif automatic.get('state') in ('WAITING_ACK','SETTLING'):
                status = '这一轮说完了，马上继续听…'
        elif automatic.get('error'): status = '对话已暂停，请检查后重新开始'
        if handsfree:
            hf_state=handsfree.get('state')
            if not handsfree.get('enabled'):status='免点击对话已暂停，麦克风已关闭'
            elif hf_state=='WAITING_PERSON':status='正对汐蓝，开口就能聊'
            elif hf_state=='WAITING_SPEECH':status='看见你了，正在等你开口…'
            elif hf_state=='CHECKING_SPEECH':status='正在听清你的话…'
            elif hf_state=='WAITING_SERVICE':status='正在等待语音服务恢复…'
            elif hf_state=='COOLDOWN':status='稍等，正在重新准备聆听…'
            timing=handsfree.get('listening_timing',{})
            if timing.get('enabled') and hf_state in ('PREPARING_SPEECH','WAITING_SPEECH'):
                status=('我在听，正在确认你的位置…' if not timing.get('entry_confirmed') else '我在听，直接说就好…') if timing.get('input_ready') else '正在准备麦克风…'
            elif timing.get('enabled') and hf_state=='CONFIRMING_SPEECH':status='这一句先保留，正在确认你的位置…'
        barge=state.get('voice_barge_in',{})
        if barge.get('continuation_listening') and handsfree.get('listening_timing',{}).get('input_ready'):
            status='这句说完了，我在听下一句…'
        if handsfree.get('enabled') and state.get('playing') and barge.get('listening') and barge.get('echo_reference_ready'):
            status='正在回答，你可以直接开口打断'
        self.status.set_text(status)
        target,identity = modules.get('target',{}), modules.get('identity',{})
        people = modules.get('vision',{}).get('people_count')
        count_label = '人脸：' if modules.get('vision',{}).get('count_kind') == 'faces' else '人数：'
        target_text = STATE_TEXT.get(target.get('state'),'待接入')
        if camera_only and target.get('state') == 'NONE':target_text = '无目标'
        if target.get('selected'):target_text += ' #'+str(target['selected']['track_id'])
        identity_text = identity.get('display_name') or display_state('identity',identity.get('state'))
        self.insight_labels['people'].set_text(str(people)+' 人' if people is not None else '等待检测')
        self.insight_labels['target'].set_text(target_text)
        self.insight_labels['identity'].set_text(identity_text)
        self.insight_labels['identity'].set_tooltip_text(identity.get('detail', '身份服务尚未接入'))
        transcript = transcription.get('text') or interaction.get('transcript') or '等待你的声音…'
        if local_recording_active:transcript = '正在聆听…'
        elif transcription.get('state') == 'CANCELLED':transcript = '本轮已取消。'
        elif transcription.get('state') == 'TRANSCRIBING':transcript = '正在识别这段录音…'
        elif transcription.get('state') == 'ERROR':transcript = '识别失败，请检查转写服务后重试。'
        elif transcription.get('state') == 'EMPTY':transcript = '没有听清，请再说一次。'
        elif transcription.get('state') == 'DISABLED' and local_recording.get('state') == 'READY':
            transcript = '录音已完成，转写服务尚未连接。'
        self.transcript_label.set_text(transcript)
        self.transcript_label.set_tooltip_text(transcription.get('error') or transcript)
        reply = interaction.get('reply') or ('本轮已取消。' if interaction.get('state') == 'CANCELLED' else
                    '我在这里，准备好就开始说话吧。\n语音主机连接后，将在这里显示回答。')
        if local_busy and state.get('reply'):
            reply = state['reply']
        if not local_busy and not interaction.get('reply') and local_recording.get('state') == 'READY':
            reply = ('文字已显示在上方。问答服务连接后，汐蓝将在这里回答。' if transcription.get('state') == 'READY'
                     else '录音已完成，正在等待文字转写。问答服务连接后再生成回答。'
                     if transcription.get('state') == 'TRANSCRIBING' else
                     '录音已完成。语音服务尚未连接，暂未生成识别内容和回答。')
        elif local_recording_active:
            reply = ('我在听，你说完后我会自动回答。' if automatic.get('enabled') or handsfree.get('enabled') else
                     '正在聆听。再次点击“停止录音”结束，点击“取消本轮”丢弃录音。')
        if transcription.get('voice_reply'):reply=transcription['voice_reply']['reply_text']
        elif transcription.get('service',{}).get('streaming') and state.get('reply'):reply=state['reply']
        elif local_conversation and transcription.get('state')=='TRANSCRIBING':reply='稍等，我在听懂并准备回答。'
        elif local_conversation and not local_recording_active and transcription.get('state') in {'IDLE','DISABLED'}:
            reply=('我在呢，正对我开口就能聊天。' if handsfree.get('enabled') else
                   '免点击对话已暂停，点“恢复免点击”后我会等你开口。' if handsfree else
                   '我在呢，点一下开始对话，就可以直接和我聊天。' if self.config.get('automatic_turns') else
                   '我在呢，点一下开始录音，聊完再点停止。')
        if reply != self.reply_text:
            self.reply_view.get_buffer().set_text(reply)
            self.reply_text = reply
        timings = interaction.get('timings_ms',{})
        self.latency_label.set_text(' · '.join(label+' '+(str(round(timings[key]))+'ms' if key in timings else '—')
            for key,label in [('first_audio','首声'),('asr','ASR'),('vlm','VLM'),('tts','TTS')]))
        recording = local_recording_active or audio.get('state') == 'RECORDING'
        self.record_button.set_label('停止录音' if recording else '开始录音')
        local_capture = local_recording_active or (audio.get('state') != 'RECORDING' and not caps.get('record_start'))
        record_available = (local_recording.get('can_stop' if recording else 'can_start') if local_capture
                            else caps.get('record_stop' if recording else 'record_start'))
        self.record_button.set_sensitive(bool(record_available) and not local_busy
            and not state['avatar_command_pending'] and not view['pending_count'] and (recording or not remote_busy))
        self.record_button.set_tooltip_text('点击开始，再次点击停止；最长录音20秒' if record_available else '请先结束当前播放或录音')
        if self.config.get('automatic_turns'):
            self.record_button.set_label('结束对话' if automatic.get('enabled') else '开始对话')
            self.record_button.set_sensitive(bool(automatic.get('can_stop') or
                automatic.get('can_start') and not state['avatar_command_pending'] and not view['pending_count'] and not remote_busy))
            self.record_button.set_tooltip_text('停止聆听并结束当前回答' if automatic.get('enabled') else
                '开启后说完自动接话；汐蓝回答完会继续听下一句')
            self.interaction_cancel.set_tooltip_text('取消当前录音或回答，并结束连续对话')
        if handsfree:
            self.record_button.set_label('结束并暂停' if handsfree.get('conversation_entered') else
                                         '暂停免点击' if handsfree.get('enabled') else '恢复免点击')
            self.record_button.set_sensitive(not state['avatar_command_pending'])
            self.record_button.set_tooltip_text('暂停会关闭麦克风，并保持暂停直到再次开启')
        preview_ref = snapshot.get('preview') if snapshot else None
        frame_fresh = bool(preview_ref and time.monotonic()*1000-preview_ref['captured_mono_ms'] <= 1500)
        frame_fresh = frame_fresh and preview_ref==display['frame_reference']
        self.ask_button.set_sensitive(bool(caps.get('ask_frame')) and frame_fresh and not local_busy and not local_recording_active
                                      and not remote_busy and not view['pending_count'])
        self.ask_button.set_tooltip_text('使用当前画面发起问答' if caps.get('ask_frame') else '当前图问答尚未接入')
        for name in ('target_select','identity_enroll','identity_delete'):
            self.controls[name].set_sensitive(bool(caps.get(name)) and not view['pending_count'])
            self.controls[name].set_tooltip_text('操作由身份与目标服务确认' if caps.get(name) else '功能尚未接入')
        self.controls['identity_enroll'].set_sensitive(bool(identity) and not view['pending_count'])
        self.controls['vision_target_select'].set_sensitive(self.controls['target_select'].get_sensitive())
        self.controls['vision_target_select'].set_tooltip_text(self.controls['target_select'].get_tooltip_text())
        self.controls['vision_identity'].set_sensitive(bool(identity)
            and not view['pending_count'])
        self.controls['vision_identity'].set_tooltip_text(identity.get('detail') or '身份服务尚未接入')
        for index in range(len(self.lines)):
            self.controls['demo_'+str(index)].set_sensitive(not remote_busy and not local_recording_active)
        image=display['frame_visible']
        # Freshness controls the placeholder/actions, never the native XID.
        # Hiding this canvas on a late frame can leave an obsolete drawable
        # after remapping. The worker already clears expired pixels.
        self.preview_image.set_visible(True)
        if self.large_preview:
            self.large_preview_note.set_text('实时画面 · '+count_label+str(people) if image and people is not None else
                '实时画面 · 等待检测结果' if image else '画面已失联或过期，等待重新连接')
        self.preview_expand.set_sensitive(bool(image))
        self.preview_placeholder.set_visible(self.preview_output.placeholder_visible(display, modules.get('camera',{}).get('state')) if self.preview_output else not bool(image))
        self.preview_placeholder.set_text('当前画面已失联或过期' if modules.get('camera',{}).get('state') == 'LOST' else
            '等待视觉画面\n接入后显示当前画面与目标')
        self.vision_note.set_text(('界面预览 · 示例数据，非实时采集。' if fixture else
                                  identity.get('detail') or '点击“放大画面”查看细节，或选择要关注的目标。') if image else
                                 '等待摄像头画面，恢复后继续显示追踪结果。')
        self.vision_summary.set_text(('示例解读：' if fixture else '')+
            ('画面中检测到 '+str(people)+' 人。\n'+
             ('当前关注目标 #'+str(target['selected']['track_id'])+'。' if target.get('selected') else '尚未选择跟随目标。')+
             ('\n目标身份：'+identity['display_name']+'。' if identity.get('display_name') else '')
             if image and people is not None else '等待新鲜画面与检测结果。'))
        values = {key:(display_state(key,modules.get(key,{}).get('state')), modules.get(key,{}).get('state'))
                  for key in ('camera','vision','target','identity','motion','host','audio')}
        if not modules.get('camera') and self.device_inventory['camera_present']:
            values['camera'] = ('已枚举','UNKNOWN')
        if not audio and state['ui_settings']['available']:
            values['audio'] = ('音响就绪','READY')
        if local_recording_active:
            values['audio'] = ('正在录音','RECORDING')
        elif local_recording.get('error'):
            values['audio'] = ('录音失败','ERROR')
        values['touch'] = ('已连接','READY') if self.touch_inputs else ('未检测到','UNKNOWN')
        lan = self.device_inventory['lan']
        values['network'] = ('已连接','READY') if lan is True else ('网线未连接','OFFLINE') if lan is False else ('未检测到','UNKNOWN')
        for key,(value,status_code) in values.items():
            label = self.device_cards[key]
            if label.get_text()!=value:label.set_text(value)
            label.set_tooltip_text(modules.get(key,{}).get('detail') or value)
            style = label.get_style_context()
            desired=('bad' if status_code in ('ERROR','FAULT','FAILED','LOST') else
                            'good' if status_code in ('READY','KNOWN','CONFIRMED') else
                            'unknown' if status_code in (None,'UNKNOWN') else 'warn')
            if not style.has_class(desired):
                for name in ('good','warn','bad','unknown'):style.remove_class(name)
                style.add_class(desired)
        self.device_note.set_text(('测试数据 · ' if fixture else '')+link_text)
        self.connection_label.set_text(link_text+(' · 配置文件需要修复' if self.connection_store.error else ''))
        self.connection_label.set_tooltip_text(view['error'] or self.connection_store.error or link_text)
        self.host_status_label.set_text('语音主机：'+values['host'][0])
        if view['results']:
            result = view['results'][-1]
            from board.interaction.ui_contract import identity_completion
            completed = identity_completion(result, identity)
            # The matching COMMITTED snapshot can arrive after the HTTP ACK.
            # Revisit that same command when its transaction actually completes.
            result_key = (result['command_id'], completed)
            if result_key != self.last_service_result:
                self.last_service_result = result_key
                self.toast = completed or ('请求已受理，等待服务状态更新' if result.get('accepted') else
                              '操作结果待确认' if result.get('outcome') == 'UNKNOWN' else
                              result.get('detail') or '请求未被接受')
                self.toast_until = time.monotonic()+3
        recent = [row['interval_ms'] for row in list(self.samples)[-8:] if row['interval_ms']]
        fps = round(1000/(sum(recent)/len(recent)),1) if recent else 0
        footer = ('相机 '+values['camera'][0]+'   DPU '+STATE_TEXT.get(modules.get('npu',{}).get('state'),'待接入')+
                  '   PL '+STATE_TEXT.get(modules.get('pl',{}).get('state'),'待接入')+'   '+settings_text+'   LAN '+values['network'][0]+
                  '   保存 本地   隐私 待接入   模式 '+('测试' if fixture else '接入' if snapshot else '本地')+'   屏幕 '+str(fps)+'fps')
        presentation_footer = ('演示层   ·   '+('视觉追踪' if self.page == 'vision' else '设置' if self.page == 'settings' else '玩偶交流')+
                               '   ·   '+settings_text+'   ·   '+
                               ('示例数据' if fixture else '语音主机 '+values['host'][0]))
        self.footer.set_text(self.toast if time.monotonic() < self.toast_until else
                             footer if self.ui_layer == 'debug' else presentation_footer)
        self.runtime_view = {k:v for k,v in view.items() if k not in ('preview','identity_face')}
        self.runtime_view.update(protocol_version='aura-ui-1',frame_visible=bool(image),
                                 frame_reference=display['frame_reference'])
        self.runtime_view['preview_metrics']=display
        state.update(ui_runtime=self.runtime_view,ui_pages=list(self.page_names),ui_layer=self.ui_layer)

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
        if data.get('type') == 'preview_open':
            return self.open_preview()
        kind = data['type']
        if kind == 'asr_config':
            values = self.transcription_store.update(data['values'])
            command = self.controller.configure_transcription(values)
            return {'ok':True,'queued':True,'command_id':command,'message':'转写服务设置已保存'}
        if kind == 'profile_dialog':
            from tools.profile_selection_ui import profile_dialog
            return profile_dialog(self)
        if kind == 'ui_layer':
            self.show_layer(data.get('layer') or ('debug' if self.ui_layer == 'presentation' else 'presentation'))
            return {'ok':True,'message':'已切换到'+('调试层' if self.ui_layer == 'debug' else '演示层')}
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
        if kind == 'conversation_toggle' or kind == 'record_toggle' and getattr(self,'config',{}).get('automatic_turns'):
            if getattr(self,'config',{}).get('handsfree_dialogue'):
                intent=self.controller.handsfree_toggle()
                return {'ok':True,'queued':True,'command_id':intent,'message':'正在切换免点击对话'}
            automatic = self.controller.public().get('automatic_conversation',{})
            if not automatic.get('enabled'):
                snapshot = self.services.read()['snapshot']
                modules = snapshot.get('modules',{}) if snapshot else {}
                if (modules.get('audio',{}).get('state') in ('RECORDING','PLAYING') or
                        modules.get('interaction',{}).get('state') in ('LISTENING','PROCESSING','SPEAKING')):
                    raise ValueError('请先结束当前交互')
            method = 'conversation_stop' if automatic.get('enabled') else 'conversation_start'
            selection=getattr(getattr(self,'transcriber',None),'conversation_selection',None)
            if method=='conversation_start' and selection is not None:
                resume=False
                if selection.saved is not None:
                    dialog=self.Gtk.Dialog(title='开始聊天',transient_for=self.window,modal=True)
                    dialog.get_content_area().add(self.Gtk.Label(label='继续上次的话题，或开始一段新的对话。'))
                    for label,response in [('返回',self.Gtk.ResponseType.CANCEL),('新对话',self.Gtk.ResponseType.NO),
                                           ('继续上次',self.Gtk.ResponseType.YES)]:
                        dialog.add_button(label,response).set_size_request(140,54)
                    dialog.show_all();response=dialog.run();dialog.destroy()
                    if response not in (self.Gtk.ResponseType.YES,self.Gtk.ResponseType.NO):
                        return {'ok':True,'message':'已返回'}
                    resume=response==self.Gtk.ResponseType.YES
                self.transcriber.select_conversation(resume=resume)
            intent = getattr(self.controller,method)()
            return {'ok':True,'queued':True,'command_id':intent,'message':'正在结束对话' if automatic.get('enabled') else '正在开启对话'}
        if kind == 'record_toggle':
            snapshot = self.services.read()['snapshot']
            local = self.controller.public().get('local_recording',{})
            recording = (local.get('state') == 'RECORDING' or
                         snapshot and snapshot['modules'].get('audio',{}).get('state') == 'RECORDING')
            return self.command({'type':'service_action','action':'record_stop' if recording else 'record_start'})
        if kind == 'service_action':
            if data['action'] == 'cancel':
                return self.command({'type':'event','event':'cancel'})
            local = self.controller.public()
            view = self.services.read()
            snapshot = view['snapshot']
            caps = snapshot['capabilities'] if snapshot else {}
            recording = local.get('local_recording',{})
            modules = snapshot['modules'] if snapshot else {}
            use_local = recording.get('can_stop') or (not caps.get('record_start') and modules.get('audio',{}).get('state') != 'RECORDING')
            if data['action'] in ('record_start','record_stop') and use_local:
                if (modules.get('audio',{}).get('state') in ('RECORDING','PLAYING') or
                        modules.get('interaction',{}).get('state') in ('LISTENING','PROCESSING','SPEAKING')):
                    raise ValueError('请先结束当前交互')
                intent = getattr(self.controller,data['action'])()
                return {'ok':True,'queued':True,'command_id':intent,'message':'录音操作已排队'}
            if data['action'] == 'ask_frame' and recording.get('can_stop'):
                raise ValueError('请先停止录音')
            if data['action'] in ('record_start','ask_frame') and (local['phase'] != 'IDLE' or local['avatar_command_pending']):
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
            intent = self.controller.submit(line['text'], line['emotion'], line['action'])
            return {'ok':True,'queued':True,'command_id':intent,'message':'演示已排队'}
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
            if self.diagnostic_result:
                completed,self.diagnostic_result = self.diagnostic_result,None
                self.toast = completed.get('error') or '诊断已保存'
                self.toast_until = time.monotonic()+2
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
            packet = self.controller.read()
            if self.native_video:
                self.last_image=packet['image']
                self.last_avatar_sequence=packet['sequence']
            if not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:
                self.last_image = packet['image']
                self.current_pixbuf = self.Pixbuf.Pixbuf.new_from_bytes(self.GLib.Bytes.new(packet['rgb']),
                    self.Pixbuf.Colorspace.RGB,False,8,self.rect['w'],self.rect['h'],self.rect['w']*3)
                self.portrait.set_from_pixbuf(self.current_pixbuf)
                self.last_avatar_sequence = packet['sequence']
                self.displayed_frames += 1
            # Portrait and intents keep their own cadence; expensive labels/settings
            # only need 10 Hz. Audio/VAD still run on the render owner.
            if time.monotonic()-self.last_runtime_refresh < .1:
                return True
            self.last_runtime_refresh = time.monotonic()
            state = packet['state']
            state['avatar_display']={'frames':self.displayed_frames,'sequence':self.last_avatar_sequence,'at':time.monotonic()}
            if self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')
            settings_text = self.refresh_settings(state)
            state.update(character=self.character, dialogue_enabled=bool(state.get('local_transcription',{}).get('service',{}).get('conversation')), backend='gtk3-gstreamer', cached_only=True)
            status = '已暂停' if state['paused'] else {'IDLE':'等你开口','VOICE_PREPARING':'正在准备声音…',
                'VOICE_STARTING':'正在准备播放…','SPEAKING':'正在说话','ACTION':'正在回应'}.get(state['phase'],state['phase'])
            self.demo_status.set_text('本地演示 · '+(state['error'] or status))
            self.reply.set_text(state['reply'])
            self.refresh_runtime(state,settings_text)
            self.samples.append({'t':state['visual_time'],'interval_ms':interval,
                'render_ms':(time.perf_counter()-started)*1000,**{key:state[key] for key in
                ('phase','state','asset','index','speech_gain','mouth_level','blink_active','playing','paused','audio_time')}})
            state['ui_tick_ms']=round((time.perf_counter()-started)*1000,2)
            state['diagnostic_job']=dict(self.diagnostic_job) if self.diagnostic_job else None
            self.bridge.publish(state,packet['jpeg'])
        except Exception as exc:
            message = type(exc).__name__+': '+str(exc)
            if not self.errors or self.errors[-1] != message:
                self.errors.append(message)
                print('STAGE ERROR '+message, flush=True)
            self.controller.cancel()
            self.status.set_text(message)
        return True

    def save_evidence(self):
        from tools.realtime_metrics import summarize
        if self.diagnostic_thread and self.diagnostic_thread.is_alive():
            return dict(self.diagnostic_job,message='正在保存诊断',ok=True,queued=True)
        stamp = str(time.time_ns())
        # Only widget geometry is read on GTK's thread. Encoding, X11 capture
        # and file writes run in one bounded background job.
        rows = list(self.samples)[-2000:]
        avatar_jpeg = self.controller.read()['jpeg']
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
            'preferences':self.preferences,'ui_page':self.page,'ui_layer':self.ui_layer,'touch_devices':self.touch_inputs,
            'input_events':list(self.input_events),
            'ui_runtime':self.runtime_view,'device_inventory':self.device_inventory,
            'ui_geometry':{'width':self.window.get_allocated_width(),'height':self.window.get_allocated_height(),
                           'visible_controls':controls,'dialogs':dialogs},
            'scope':'RUN_LOG_NOT_AUTOMATIC_ACOUSTIC_OR_FULL_SYSTEM_ACCEPTANCE'}
        path = self.evidence_root/('stage_'+stamp+'.json')
        screenshot = self.evidence_root/('window_'+stamp+'.png')
        report['screenshot_path']=str(screenshot)
        report['diagnostic_id']=stamp
        self.diagnostic_job={'diagnostic_id':stamp,'report':str(path),'state':'PENDING'}
        def save():
            try:
                if avatar_jpeg:
                    (self.evidence_root/('frame_'+stamp+'.jpg')).write_bytes(avatar_jpeg)
                # Keep the native X11 reader isolated from GTK/Cairo.
                captured=subprocess.run([sys.executable,'-B',str(AURA/'tools/board_screen_capture.py'),
                    str(screenshot)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3)
                if captured.returncode:
                    raise RuntimeError('屏幕诊断读取失败：'+captured.stderr.decode(errors='replace')[-500:])
                latest=self.evidence_root/'latest_verification.json'
                for target,value in ((latest,{k:v for k,v in report.items() if k!='samples'}),(path,report)):
                    temp=target.with_name(target.name+'.tmp-'+stamp)
                    temp.write_text(json.dumps(value,ensure_ascii=False)+'\n',encoding='utf-8')
                    temp.replace(target)
                self.diagnostic_job=dict(self.diagnostic_job,state='COMPLETE')
                self.diagnostic_result={'ok':True}
            except Exception as exc:
                self.diagnostic_job=dict(self.diagnostic_job,state='FAILED',error=str(exc))
                self.diagnostic_result={'ok':False,'error':'诊断保存失败：'+str(exc)}
        self.diagnostic_thread=threading.Thread(target=save,name='aura-ui-diagnostic',daemon=True)
        self.diagnostic_thread.start()
        return dict(self.diagnostic_job,ok=True,queued=True,message='正在保存诊断')

    def cleanup(self):
        self.close_identity_face_dialog()
        if self.diagnostic_thread:
            self.diagnostic_thread.join(timeout=4)
        if self.preview_output:
            self.preview_output.close()
            self.preview_output = None
        if self.controller:
            self.controller.close()
            self.controller = None
        if self.native_video:
            self.native_video.close();self.native_video=None
        if self.native_pixels:
            self.native_pixels.close();self.native_pixels=None
        if getattr(self,'transcriber',None):
            self.transcriber.close()
            self.transcriber = None
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
        self.close_identity_face_dialog()
        if self.timer:
            self.GLib.source_remove(self.timer)
        if self.foreground_timer:
            self.GLib.source_remove(self.foreground_timer)
        try:
            if self.config.get('handsfree_dialogue'):
                # Closing the UI must release audio without changing the
                # explicit monitoring preference to "paused".
                self.controller.close()
            else:
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
