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
    def __init__(self, root, config, evidence_root, *, windowed=False):
        from PIL import Image
        from board.interaction import avatar_board
        from board.runtime.character import CHARACTER_NAME, DEMO_LINES
        from tools.demo_script import create_demo_core
        from tools.gstreamer_audio import GStreamerAudioOutput
        from tools.realtime_bridge import StageBridge
        from tools.realtime_controller import RealtimeController
        from tools.selected_voice_service import SpeechJobs, VoiceWorker
        from tools.pillow_compat import LANCZOS

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
                     'realtime_facials.py', 'facial_layers.py', 'pillow_compat.py', 'selected_voice_service.py'):
            self.source_hashes['tools/' + name] = hashlib.sha256((AURA/'tools'/name).read_bytes()).hexdigest()
        reuse = AURA.parent/'deliverables/2026-10-06_avatar_reuse/preview_script.py'
        self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py'] = hashlib.sha256(reuse.read_bytes()).hexdigest()
        self.config = config
        self.font_hash = register_font(AURA/config['font_file'])
        initialized = self.Gtk.init_check([])
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            raise RuntimeError('Cannot connect to the current X display')
        self.jobs = self.output = self.bridge = None
        self.closed = False
        self.errors, self.samples = [], deque(maxlen=10000)
        self.last_tick = self.last_publish = None
        self.last_image = self.current_pixbuf = None
        self.timer = None
        try:
            core = create_demo_core('reuse')
            core.MAX_CACHED_SEQUENCES = int(config['cache_sequences'])
            self.jobs = SpeechJobs(self.root, VoiceWorker(self.root, cached_only=True))
            self.output = GStreamerAudioOutput(self.evidence_root/'audio_worker.log', config['audio_device'])
            self.controller = RealtimeController(core, self.jobs, self.output)
            self.bridge = StageBridge(self.root, int(config['browser_port']))
            self.build_window(windowed)
            # Slow ARM frames must yield to GTK's higher-priority redraw source.
            self.timer = self.GLib.timeout_add(int(config['tick_ms']), self.tick,
                                             priority=self.GLib.PRIORITY_DEFAULT_IDLE)
        except Exception:
            self.cleanup()
            raise

    def label(self, text, x, y, width, height, name=None):
        label = self.Gtk.Label(label=text)
        label.set_xalign(0)
        label.set_yalign(0.5)
        label.set_line_wrap(True)
        if name:
            label.set_name(name)
        label.set_size_request(width, height)
        self.fixed.put(label, x, y)
        return label

    def button(self, label, data, x, y, width, height):
        button = self.Gtk.Button(label=label)
        button.set_size_request(width, height)
        button.connect('clicked', lambda unused: self.native(data))
        self.fixed.put(button, x, y)
        return button

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
               'button {padding:6px;border-radius:7px;background:'+colors['bg']+';color:'+colors['text_primary']+';}'
               '#title {font-size:26px;color:'+colors['accent_dark']+';}'
               '#avatar_title {color:'+colors['text_secondary']+';}'
               '#status {color:'+colors['accent_dark']+';}')
        provider = gtk.CssProvider()
        provider.load_from_data(css.encode())
        gtk.StyleContext.add_provider_for_screen(self.Gdk.Screen.get_default(), provider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        pad = self.layout['left_panel']['padding']
        left_width = self.layout['left_panel']['x1'] - pad*2
        self.label(self.character, pad, 12, left_width, 36, 'title')
        self.label('选择一句话，听听汐蓝的回应。', pad, 56, left_width, 30)
        self.status = self.label('等你开口', pad, 98, left_width, 38, 'status')
        self.reply = self.label('', pad, 148, left_width, 102)
        button_width = (left_width-12)//2
        for index,line in enumerate(self.lines):
            self.button(line['label'], {'type':'demo','index':index}, pad+(index%2)*(button_width+12),
                        264+(index//2)*76, button_width, 62)
        self.pause_button = self.button('暂停 / 继续', {'type':'pause'}, pad, 424, button_width, 48)
        self.button('打断', {'type':'event','event':'cancel'}, pad+button_width+12, 424, button_width, 48)
        self.button('重新开始', {'type':'event','event':'reset'}, pad, 486, button_width, 44)
        self.button('保存记录', {'type':'save_evidence'}, pad+button_width+12, 486, button_width, 44)
        panel = self.layout['right_panel']
        self.label(self.character, panel['x0']+panel['padding'], panel['y0']+panel['padding'],
                   panel['x1']-panel['x0']-2*panel['padding'], self.layout['right_inner']['label_h'], 'avatar_title')
        self.portrait = gtk.Image()
        self.fixed.put(self.portrait, self.geometry['x']+self.rect['x'], self.geometry['y']+self.rect['y'])
        bar = self.layout['bottom_bar']
        self.footer = self.label('等待对话', 8, bar['y0']+4, width-16, bar['height']-8)
        self.window.show_all()
        if not windowed:
            self.window.fullscreen()

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
            state.update(character=self.character, dialogue_enabled=False, backend='gtk3-gstreamer', cached_only=True)
            status = '已暂停' if state['paused'] else {'IDLE':'等你开口','VOICE_PREPARING':'正在准备声音…',
                'VOICE_STARTING':'正在准备播放…','SPEAKING':'正在说话','ACTION':'正在回应'}.get(state['phase'],state['phase'])
            self.status.set_text(state['error'] or status)
            self.reply.set_text(state['reply'])
            self.footer.set_text(status)
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
            'errors':self.errors,'samples':rows,'scope':'RUN_LOG_NOT_AUTOMATIC_ACOUSTIC_OR_FULL_SYSTEM_ACCEPTANCE'}
        path = self.evidence_root/('stage_'+stamp+'.json')
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (self.evidence_root/'latest_verification.json').write_text(json.dumps({k:v for k,v in report.items() if k!='samples'},
            ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return {'ok':True,'report':str(path),'stats':report['stats']}

    def cleanup(self):
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
    stage = BoardAvatarStage(args.root, config, evidence, windowed=args.windowed)
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
