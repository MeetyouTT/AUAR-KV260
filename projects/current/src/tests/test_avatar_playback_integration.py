"""Regression tests at the real Tk tick / Qt draw / event-bus boundaries."""
import json
import os
import random
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PIL import Image
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication
from board.interaction.avatar_player import AvatarPlayer
from board.interaction.qt_widgets import AvatarPanel
from board.interaction.ui_state import UiState
from board.runtime.event_bus import EventBus, EventEnvelope
from board.runtime.events import EventType as E
from board.runtime.fsm import RuntimeFSM
from tools.demo_stage import StageApp, StageCore
from tools import demo_stage


@pytest.fixture(scope='module')
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sprites(tmp_path):
    for name in ['idle_normal', 'talking_neutral', 'talking_neutral_b',
                 'talking_neutral_c', 'talking_normal', 'ack_nod', 'emo_surprised']:
        d = tmp_path / name
        d.mkdir()
        count = 22 if name in ('emo_surprised', 'ack_nod') else 39
        for i in range(count):
            Image.new('RGBA', (32, 40), (i * 5, 70, 100, 255)).save(d / ('%06d.png' % i))
        (d / 'meta.json').write_text(json.dumps({'size': [32, 40], 'fps': 24,
                                               'frames': count}), encoding='utf-8')
        if count == 39:
            (d / 'segments.json').write_text(json.dumps({'enter': [0, 3],
                'loop': [4, 11], 'exit': [12, 38],
                'windows': [[4, 11], [12, 19], [20, 27]]}), encoding='utf-8')
    return tmp_path


class Widget:
    def configure(self, **kwargs): pass
    def delete(self, *args): pass
    def create_image(self, *args, **kwargs): pass
    def after(self, *args): pass


class Player:
    completed = False
    def poll(self):
        result, self.completed = self.completed, False
        return result
    def is_busy(self): return False


def app(core):
    a = StageApp.__new__(StageApp)
    a.core, a.tts = core, Player()
    a.root = a.canvas = a.hud = a.state_label = Widget()
    a.ImageTk = SimpleNamespace(PhotoImage=lambda image: None)
    a._log = lambda message: None
    return a


def tick(a, now, monkeypatch):
    monkeypatch.setattr(demo_stage.time, 'monotonic', lambda: now)
    a._tick()
    return a._last_meta


def test_tk_real_tick_retains_exit_after_tts_stop(sprites, monkeypatch):
    c = StageCore(sprite_root=sprites)
    c.send(E.BOARD_KEY_PRESSED)
    c.send(E.AUDIO_VAD_END)
    c.apply_response({'emotion': 'neutral', 'reply_text': '你好'})
    a = app(c)
    tick(a, 100, monkeypatch)
    assert tick(a, 101, monkeypatch)['stage'] == 'loop'
    a.tts.completed = True
    m = tick(a, 101.3, monkeypatch)
    assert c.fsm.state.value == 'IDLE'
    assert m['display_state'] == 'SPEAKING_NEUTRAL' and m['stage'] == 'blend'
    before = m['source_position']
    m = tick(a, 101.4, monkeypatch)
    assert m['alpha'] == 0 and m['asset'] == 'talking_neutral'
    assert abs(m['source_position'] - before) <= 2.4
    stages = [tick(a, 101.3 + i / 30, monkeypatch)['stage'] for i in range(5, 65)]
    assert 'exit' in stages
    assert a._last_meta['display_state'] == 'IDLE'


def test_tk_wake_completion_advances_without_tts(sprites, monkeypatch):
    c = StageCore(sprite_root=sprites)
    c.send(E.AUDIO_KWS_DETECTED)
    a = app(c)
    a.tts = None
    tick(a, 100, monkeypatch)
    tick(a, 101, monkeypatch)
    assert c.fsm.state.value == 'LISTENING'
    assert tick(a, 101.1, monkeypatch)['display_state'] == 'LISTENING'


def test_burst_completion_is_reported_once_per_entry(sprites):
    c = AvatarPlayer(sprite_root=sprites)
    c.frame_at('AWAKE', 100)
    got = []
    for now in [101, 102, 103]:
        c.frame_at('AWAKE', now)
        got.append(c.take_burst_finished())
    assert got == [True, False, False]
    c.frame_at('IDLE', 104)
    c.frame_at('AWAKE', 105)
    c.frame_at('AWAKE', 106)
    assert c.take_burst_finished()


def test_tk_and_qt_share_frame_sequence_and_transitions(qapp, sprites):
    assert StageCore is AvatarPlayer
    c = AvatarPlayer(sprite_root=sprites, rng=random.Random(11))
    panel = AvatarPanel(UiState(), sprite_root=sprites)
    panel._player.rng = random.Random(11)
    for i in range(660):
        now = 100 + i / 30
        state = 'SPEAKING_NEUTRAL' if i < 600 else 'IDLE'
        expected = c.display_frame(state, now)
        actual = panel.sample_frame(state, now, {'runtime_state': state})
        for key in ['asset', 'index', 'stage', 'alpha', 'display_state', 'transitioning']:
            assert actual[key] == expected[key], (i, key)
    assert panel._last_meta['display_state'] == 'IDLE'


def test_qt_real_draw_sends_wake_completion_to_fsm(qapp, sprites, monkeypatch):
    bus = EventBus(dispatch_async=False)
    fsm = RuntimeFSM(bus=bus)
    ui = UiState(event_bus=bus)
    panel = AvatarPanel(ui, sprite_root=sprites)
    bus.publish(EventEnvelope(E.AUDIO_KWS_DETECTED, 'test', 0))
    seen = []
    bus.subscribe(lambda env: seen.append(env), {E.AUDIO_PLAYBACK_STOP})
    for now in [100, 101, 101.1]:
        monkeypatch.setattr(demo_stage.time, 'monotonic', lambda: now)
        image = QImage(439, 556, QImage.Format_ARGB32)
        painter = QPainter(image)
        try:
            panel._render_avatar(painter, QRect(0, 0, 439, 556), panel.style, ui.snapshot())
        finally:
            painter.end()
    assert fsm.state.value == 'LISTENING' and ui.snapshot()['runtime_state'] == 'LISTENING'
    assert len(seen) == 1 and seen[0].payload['reason'] == 'wake_animation_finished'


def test_short_speech_exits_during_enter_without_waiting(sprites):
    c = AvatarPlayer(sprite_root=sprites)
    c.display_frame('SPEAKING_NEUTRAL', 100)
    m = c.display_frame('IDLE', 100.05)
    assert m['stage'] == 'blend' and m['transitioning']


def test_cached_sequences_are_bounded(sprites):
    c = AvatarPlayer(sprite_root=sprites)
    for state in ['IDLE', 'SPEAKING_NEUTRAL', 'AWAKE', 'THINKING', 'LISTENING']:
        c.sequence(state)
    assert len(c._seq_cache) <= c.MAX_CACHED_SEQUENCES


def test_qt_retries_completion_when_sink_temporarily_rejects(qapp, sprites, monkeypatch):
    ui = UiState()
    panel = AvatarPanel(ui, sprite_root=sprites)
    calls = []
    def sink(event, payload):
        calls.append((event, payload))
        return len(calls) == 2
    monkeypatch.setattr(ui, 'emit_avatar_event', sink)
    for now in [100, 101, 101.1, 102]:
        panel.sample_frame('AWAKE', now, {'runtime_state': 'AWAKE'})
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert panel._completion_pending is None


def test_qt_action_completion_keeps_response_emotion(qapp, sprites):
    bus = EventBus(dispatch_async=False)
    fsm = RuntimeFSM(bus=bus)
    ui = UiState(event_bus=bus)
    for event, payload in [(E.BOARD_KEY_PRESSED, {}), (E.AUDIO_VAD_END, {}),
            (E.DIALOGUE_RESPONSE_RECEIVED, {'emotion': 'happy', 'avatar_action': 'ack_nod', 'reply_text': '好呀'})]:
        bus.publish(EventEnvelope(event, 'test', 0, payload))
    assert fsm.state.value == 'ACK_NOD'
    ui.set_device('audio', 'busy', 'playback')
    panel = AvatarPanel(ui, sprite_root=sprites)
    panel.sample_frame('ACK_NOD', 100, ui.snapshot())
    panel.sample_frame('ACK_NOD', 101, ui.snapshot())
    assert fsm.state.value == 'SPEAKING'


def test_cancel_before_worker_start_cannot_relabel_old_request(sprites, monkeypatch):
    c = StageCore(sprite_root=sprites)
    a = app(c)
    a.busy = False
    a.entry = SimpleNamespace(get=lambda: '你好')
    a._reply_var = SimpleNamespace(set=lambda value: pytest.fail('old response was displayed'))
    a.root = SimpleNamespace(after=lambda delay, callback: callback())
    a.tts.stop = lambda: None
    requests, threads = [], []
    def send(request, **kwargs):
        requests.append(request)
        return SimpleNamespace(to_dict=lambda: {'reply_text': '旧回复', 'emotion': 'neutral'})
    a.adapter = SimpleNamespace(send_request=send)
    class DeferredThread:
        def __init__(self, target, args, **kwargs):
            self.target, self.args = target, args
            threads.append(self)
        def start(self): pass
    monkeypatch.setattr(demo_stage.threading, 'Thread', DeferredThread)
    a._send_llm()
    gen = c.talk_gen
    a.cancel_talk()
    threads[0].target(*threads[0].args)
    assert requests[0].audio_generation_id == gen < c.talk_gen
    assert c.reply_text == ''
