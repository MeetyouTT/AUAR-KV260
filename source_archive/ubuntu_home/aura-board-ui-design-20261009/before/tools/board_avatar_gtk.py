"""KV260 GTK3 cached-voice stage; original FSM, mouths and eyelids are reused."""
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

        self.Image, self.LANCZOS = Image, LANCZOS
        self.Gtk, self.Gdk, self.Pixbuf, self.GLib = load_gtk()
        self.root = Path(root).resolve(strict=True)
        self.evidence_root = Path(evidence_root)
        self.evidence_root.mkdir(parents=True, exist_ok=False)
        self.lines, self.character = DEMO_LINES, CHARACTER_NAME
        self.layout, self.tokens = avatar_board.load_layout(), avatar_board.load_tokens()
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
        self.config = config
        self.font_hash = register_font(AURA/config['font_file'])
        initialized = self.Gtk.init_check([])
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            raise RuntimeError('Cannot connect to the current X display')
        self.jobs = self.output = self.bridge = self.mixer = None
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
        self.page = 'main'
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
            self.bridge = StageBridge(self.root, int(config['browser_port']),
                                      extra_commands=('ui_settings', 'ui_page'))
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
        self.toast = result.get('error', '') if not result.get('ok') else '操作已响应'
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
        css = ('window {background:'+colors['panel_bg']+';color:'+colors['text_primary']+';font:14px "Droid Sans Fallback";}'
               'button {padding:8px;border-radius:9px;font-size:19px;background:'+colors['bg']+';color:'+colors['text_primary']+';}'
               'button:active, button.selected {background:'+colors['accent']+';color:white;}'
               'button:disabled {color:'+colors['text_secondary']+';}'
               'scale slider {min-width:32px;min-height:32px;}'
               'scale trough {min-height:8px;}'
               '#title {font-size:26px;color:'+colors['accent_dark']+';}'
               '#avatar_title {color:'+colors['text_secondary']+';}'
               '#status {color:'+colors['accent_dark']+';}')
        provider = gtk.CssProvider()
        provider.load_from_data(css.encode())
        gtk.StyleContext.add_provider_for_screen(self.Gdk.Screen.get_default(), provider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        pad = self.layout['left_panel']['padding']
        left_width = self.layout['left_panel']['x1'] - pad*2
        self.label(self.character, pad, 12, left_width, 36, 'title')
        button_width = (left_width-12)//2
        self.button('互动', {'type':'ui_page','page':'main'}, pad, 56, button_width, 48, key='page_main')
        self.button('设置', {'type':'ui_page','page':'settings'}, pad+button_width+12, 56,
                    button_width, 48, key='page_settings')
        self.pages = gtk.Stack()
        self.pages.set_size_request(left_width, 432)
        self.fixed.put(self.pages, pad, 112)
        main, settings = gtk.Fixed(), gtk.Fixed()
        for name,page in [('main',main),('settings',settings)]:
            page.set_size_request(left_width,432)
            self.pages.add_named(page,name)
        self.status = self.label('等你开口', 0, 0, left_width, 34, 'status', main)
        self.reply = self.label('', 0, 40, left_width, 74, parent=main)
        for index,line in enumerate(self.lines):
            self.button(line['label'], {'type':'demo','index':index}, (index%2)*(button_width+12),
                        120+(index//2)*76, button_width, 64, main, 'demo_'+str(index))
        self.pause_button = self.button('暂停', {'type':'pause'}, 0, 276, button_width, 64, main, 'pause')
        self.cancel_button = self.button('打断', {'type':'event','event':'cancel'}, button_width+12,
                                         276, button_width, 64, main, 'cancel')
        self.button('重新开始', {'type':'event','event':'reset'}, 0, 356, button_width, 64, main, 'reset')
        self.button('保存画面', {'type':'save_evidence'}, button_width+12, 356, button_width, 64, main, 'save')
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
        self.footer = self.label('等待对话', 8, bar['y0']+4, width-16, bar['height']-8)
        self.window.show_all()
        self.show_page('main')
        if self.preferences['fullscreen']:
            self.window.fullscreen()

    def show_page(self, page):
        if page not in ('main','settings'):
            raise ValueError('未知页面')
        self.page = page
        self.pages.set_visible_child_name(page)
        for name in ('main','settings'):
            style = self.controls['page_'+name].get_style_context()
            (style.add_class if page == name else style.remove_class)('selected')

    def volume_drag(self, widget, event, dragging):
        self.volume_dragging = dragging
        return False

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
            self.controller.last_error = str(exc)
            return {'ok':False, 'error':str(exc)}

    def command(self, data):
        kind = data['type']
        if kind == 'ui_page':
            self.show_page(data['page'])
            return {'ok':True}
        if kind == 'ui_settings':
            return self.apply_settings(data['values'])
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
                        self.controller.last_error = str(exc)
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
            self.status.set_text(state['error'] or status)
            self.reply.set_text(state['reply'])
            self.footer.set_text((self.toast if time.monotonic()<self.toast_until else status)+'  ·  '+settings_text)
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
        report = {'backend':'gtk3-gstreamer','cached_only':True,'model_loaded':False,
            'font_sha256':self.font_hash,'source_hashes_at_launch':self.source_hashes,
            'config':self.config,'state':self.controller.public(),'stats':summarize(rows),
            'errors':self.errors,'samples':rows,'ui_settings':self.mixer.read(),
            'preferences':self.preferences,'ui_page':self.page,'touch_devices':self.touch_inputs,
            'input_events':list(self.input_events),
            'scope':'RUN_LOG_NOT_AUTOMATIC_ACOUSTIC_OR_FULL_SYSTEM_ACCEPTANCE'}
        path = self.evidence_root/('stage_'+stamp+'.json')
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (self.evidence_root/'latest_verification.json').write_text(json.dumps({k:v for k,v in report.items() if k!='samples'},
            ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return {'ok':True,'report':str(path),'stats':report['stats']}

    def cleanup(self):
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
