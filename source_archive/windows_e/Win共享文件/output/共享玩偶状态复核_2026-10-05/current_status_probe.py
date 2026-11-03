import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path('E:/项目/共享文件夹/aura')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image
from tools import demo_stage as stage
from board.runtime.events import EventType as E
from board.runtime.fsm import RuntimeState
from board.interaction import avatar_assets as aa

source_paths = [ROOT / p for p in [
    'tools/demo_stage.py', 'board/runtime/fsm.py',
    'board/interaction/avatar_assets.py', 'board/interaction/avatar_fsm.py',
    'board/interaction/avatar_timing.py', 'board/interaction/qt_widgets.py',
    'board/interaction/avatar_lod.py', 'ui/ui_state.schema.json',
    'ui/avatar_board_manifest.json', 'requirements.txt']]
def fingerprints():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_paths}
result = {'date': '2026-10-05', 'environment':
          'PC logic probes; actual StageApp methods with simulated widgets/clock/TTS; no physical UI, audio, LLM or KV260',
          'source_before': fingerprints(), 'assets': [], 'states': []}

for directory in sorted((ROOT / 'assets/avatar').iterdir()):
    if not directory.is_dir():
        continue
    files = aa.list_frames(directory)
    if not files:
        continue
    meta = json.loads((directory / 'meta.json').read_text(encoding='utf-8'))
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    entries = {v['file']: v for v in manifest['entries']}
    issues = []
    sizes, modes = set(), set()
    total = 0
    for p in files:
        data = p.read_bytes()
        total += len(data)
        with Image.open(p) as img:
            sizes.add(img.size)
            modes.add(img.mode)
            img.verify()
        record = entries.get(p.name, {})
        if record.get('sha256') != hashlib.sha256(data).hexdigest():
            issues.append('hash: ' + p.name)
        if record.get('bytes') != len(data):
            issues.append('bytes: ' + p.name)
    if len(files) != meta['frames'] or len(files) != manifest['count']:
        issues.append('frame count mismatch')
    if set(entries) != {p.name for p in files}:
        issues.append('manifest file set mismatch')
    seg = aa.read_segments(directory)
    result['assets'].append({'asset': directory.name, 'frames': len(files),
        'fps': meta['fps'], 'sizes': sorted(sizes), 'modes': sorted(modes),
        'bytes': total, 'issues': issues, 'segments': seg,
        'rgb565_present': (directory / 'frames.rgb565').exists()})

for state in RuntimeState:
    c = stage.StageCore()
    c.idle_gain = 0
    frames = [c.frame_at(state.value, 100 + t) for t in (0, .5, 1.5)]
    result['states'].append({'state': state.value,
        'available': all(m is not None for m in frames),
        'asset': frames[0]['asset'] if frames[0] else None,
        'indices': [m['index'] if m else None for m in frames]})

class Widget:
    def configure(self, **kwargs):
        pass
    def delete(self, *args, **kwargs):
        pass
    def create_image(self, *args, **kwargs):
        pass
    def create_text(self, *args, **kwargs):
        pass
    def after(self, *args, **kwargs):
        pass

class Player:
    def __init__(self, completed=False):
        self.completed = completed
        self.calls = []
        self.config = SimpleNamespace(engine='test double', voice='silent')
    def poll(self):
        completed, self.completed = self.completed, False
        return completed
    def is_busy(self):
        return False
    def stop(self):
        self.calls.append('stop')
    def speak_async(self, text, **kwargs):
        self.calls.append(['speak', text])

class Variable:
    def __init__(self):
        self.value = ''
    def set(self, value):
        self.value = value

def app_for(core, player=None):
    a = stage.StageApp.__new__(stage.StageApp)
    a.core, a.tts = core, player
    a.root = a.canvas = a.state_label = a.hud = Widget()
    a.ImageTk = SimpleNamespace(PhotoImage=lambda img: None)
    a.logs = []
    a._log = a.logs.append
    a._reply_var = Variable()
    a.busy = False
    return a

# Run the real production tick method; only UI drawing, clock and TTS device are simulated.
c = stage.StageCore()
c.idle_gain = 0
c.send(E.BOARD_KEY_PRESSED)
c.send(E.AUDIO_VAD_END)
c.apply_response({'emotion': 'neutral', 'reply_text': '验证播报结束动画。'})
c.frame_at(c.fsm.state.value, 100)
c.frame_at(c.fsm.state.value, 103)
a = app_for(c, Player(completed=True))
before = {'state': c.fsm.state.value, 'stage': c.stage_state()[0]}
with patch.object(stage.time, 'monotonic', return_value=103.5):
    a._tick()
result['tts_completion_actual_tick'] = {'before': before,
    'after': {'state': c.fsm.state.value, 'stage': a._last_meta['stage'],
              'asset': a._last_meta['asset'], 'index': a._last_meta['index'],
              'exit_requested': c.stage_state()[1]}, 'logs': a.logs}

c = stage.StageCore()
c.idle_gain = 0
c.send(E.AUDIO_KWS_DETECTED)
c.frame_at(c.fsm.state.value, 100)
a = app_for(c)
trace = []
for now in (101, 101.2, 102):
    with patch.object(stage.time, 'monotonic', return_value=now):
        a._tick()
    trace.append({'time': now - 100, 'state': c.fsm.state.value,
                  'index': a._last_meta['index']})
result['wake_animation_actual_tick_without_tts'] = {'trace': trace, 'logs': a.logs}

c = stage.StageCore()
c.send(E.BOARD_KEY_PRESSED)
c.send(E.AUDIO_VAD_END)
gen = c.new_turn()
p = Player()
a = app_for(c, p)
a.busy = True
a.cancel_talk()
a._on_response({'emotion': 'neutral', 'reply_text': '取消后才到的旧回复'}, None, .1, gen)
result['cancel_actual_callbacks'] = {'state': c.fsm.state.value,
    'tts_calls': p.calls, 'display': a._reply_var.value, 'logs': a.logs,
    'passed': p.calls == ['stop'] and a._reply_var.value == ''}

qt = (ROOT / 'board/interaction/qt_widgets.py').read_text(encoding='utf-8')
result['formal_qt_source'] = {'uses_fixed_segment_time': 'avatar_timing.segment_time(' in qt,
    'uses_pool_assets': 'pool_assets(' in qt, 'uses_request_exit': 'request_exit(' in qt,
    'uses_segment_stage_time': 'segment_stage_time(' in qt}
result['dependencies_available'] = {name: importlib.util.find_spec(name) is not None
    for name in ('pytest', 'PySide6', 'cv2', 'sounddevice', 'sherpa_onnx')}
result['source_after'] = fingerprints()
result['sources_unchanged_during_probe'] = result['source_before'] == result['source_after']
result['summary'] = {'asset_directories': len(result['assets']),
    'png_frames': sum(a['frames'] for a in result['assets']),
    'png_mib': round(sum(a['bytes'] for a in result['assets']) / 1024**2, 2),
    'asset_integrity_issues': sum(len(a['issues']) for a in result['assets']),
    'states_available': sum(s['available'] for s in result['states'])}
(OUT / 'current_status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
for key in ('summary', 'tts_completion_actual_tick', 'wake_animation_actual_tick_without_tts',
            'cancel_actual_callbacks', 'formal_qt_source', 'sources_unchanged_during_probe'):
    print(key, json.dumps(result[key], ensure_ascii=False))
