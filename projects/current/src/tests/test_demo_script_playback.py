"""Script playback must exercise the production display and completion path."""
import json
import random
from types import SimpleNamespace

import pytest
from PIL import Image

from board.interaction.avatar_player import AvatarPlayer
from board.runtime.events import EventType as E
from tools import demo_script as demo


@pytest.fixture
def core(tmp_path):
    names = ['idle_normal', 'idle_present', 'idle_listening', 'idle_thinking',
             'talking_neutral', 'talking_neutral_b', 'talking_neutral_c',
             'talking_normal', 'talking_normal_b', 'talking_low',
             'ack_nod', 'emo_surprised']
    for name in names:
        d = tmp_path / name
        d.mkdir()
        count = 22 if name in ('ack_nod', 'emo_surprised') else 39
        for i in range(count):
            Image.new('RGBA', (32, 40), (i * 5, 70, 100, 255)).save(d / ('%06d.png' % i))
        (d / 'meta.json').write_text(json.dumps({'fps': 24, 'frames': count}), encoding='utf-8')
        if count == 39:
            (d / 'segments.json').write_text(json.dumps({'enter': [0, 11],
                'loop': [12, 19], 'exit': [35, 38],
                'windows': [[12, 19], [20, 27]]}), encoding='utf-8')
    c = AvatarPlayer(sprite_root=tmp_path, rng=random.Random(7))
    c.idle_gain = 0
    return c


def reply(runner, emotion='neutral', action='', dur=4):
    runner.core.send(E.BOARD_KEY_PRESSED)
    runner.core.send(E.AUDIO_VAD_END)
    runner._fire(demo.Cue(0, 'reply', {'reply_text': '你好', 'emotion': emotion,
                                   'avatar_action': action}, dur=dur), 0)


def test_wake_completes_into_listening_once(core):
    runner = demo.ScriptRunner(core)
    runner._fire(demo.Cue(0, 'event', E.AUDIO_KWS_DETECTED), 0)
    runner._sample(0)
    runner._sample(1)
    assert core.fsm.state.label == 'LISTENING'
    assert runner._sample(1.1)['display_state'] == 'LISTENING'
    runner._sample(2)
    assert len([e for e in runner.trace.events if '动作段播完' in e[1]]) == 1
    assert not runner.trace.rejected


@pytest.mark.parametrize('emotion,state', [('happy', 'SPEAKING'),
    ('neutral', 'SPEAKING_NEUTRAL'), ('sad', 'SPEAKING_LOW')])
def test_action_completes_into_reply_emotion(core, emotion, state):
    runner = demo.ScriptRunner(core)
    reply(runner, emotion, 'ack_nod')
    assert core.fsm.state.label == 'ACK_NOD'
    runner._sample(0)
    runner._sample(1)
    assert core.fsm.state.label == state
    assert runner._sample(1.1)['display_state'] == state
    runner._sample(2)
    assert len([e for e in runner.trace.events if '动作段播完' in e[1]]) == 1


@pytest.mark.parametrize('kind', ['stop', 'cancel'])
@pytest.mark.parametrize('when', [0.05, 1.5])
def test_short_and_long_speech_finish_exit_before_new_display(core, kind, when):
    runner = demo.ScriptRunner(core)
    reply(runner)
    runner._sample(0)
    if when > 0.1:
        runner._sample(1)
    runner._fire(demo.Cue(when, kind), when)
    target = core.fsm.state.label
    assert target in ('IDLE', 'PRESENT')
    m = runner._sample(when)
    assert m['display_state'] == 'SPEAKING_NEUTRAL'
    assert m['transitioning'] and m['stage'] == 'blend'
    rows = [runner._sample(when + i / 30) for i in range(1, 31)]
    assert any(m['stage'] == 'exit' and m['display_state'] == 'SPEAKING_NEUTRAL' for m in rows)
    assert rows[-1]['display_state'] == target
    assert not runner._speaking
    assert not runner.trace.rejected


def test_stop_before_action_end_does_not_restart_speech(core):
    runner = demo.ScriptRunner(core)
    reply(runner, 'happy', 'ack_nod')
    runner._sample(0)
    runner._fire(demo.Cue(0.1, 'stop'), 0.1)
    runner._sample(1)
    assert core.fsm.state.label == 'IDLE'
    assert not any('动作段播完' in e[1] for e in runner.trace.events)


def test_reset_clears_pending_exit_audio_and_trace(core):
    runner = demo.ScriptRunner(core)
    reply(runner)
    runner._sample(0)
    runner._fire(demo.Cue(0.1, 'cancel'), 0.1)
    assert runner._sample(0.1)['transitioning']
    runner.reset()
    assert not runner._speaking and not runner.trace.samples and not runner.trace.events
    assert runner._sample(0)['display_state'] == 'IDLE'
    assert not core._display_exiting


def test_full_script_and_second_run_complete_without_rejections(core):
    runner = demo.ScriptRunner(core, dt=1/30)
    for _ in range(2):
        trace = runner.run(quiet=True)
        assert not trace.errors and not trace.rejected
        states = [s for _, s in trace.states]
        assert states.count('AWAKE') == 1
        assert 'LISTENING' in states and 'ACK_NOD' in states
        assert all(s in states for s in ['SPEAKING', 'SPEAKING_NEUTRAL', 'SPEAKING_LOW'])
        assert any(r['transitioning'] and r['t'] >= 59 for r in trace.samples)
        assert len([e for e in trace.events if '动作段播完' in e[1]]) == 2
        assert trace.samples[-1]['display_state'] == 'IDLE'


def test_window_uses_same_sampling_and_replay_resets_audio(core, monkeypatch):
    """Execute the real window callbacks with a deterministic widget/clock adapter."""
    import tkinter as tk
    from PIL import ImageTk

    class Widgets:
        def __init__(self, *args, **kwargs):
            self.command = kwargs.get('command')
        def configure(self, **kwargs): pass
        def pack(self, *args, **kwargs): pass
        def delete(self, *args): pass
        def create_image(self, *args, **kwargs): pass
        def create_text(self, *args, **kwargs): pass
        def insert(self, *args): pass
        def see(self, *args): pass
        def title(self, *args): pass
        def bind(self, event, callback): self.replay = callback
        def after(self, delay, callback): self.pending.append(callback)
        def mainloop(self):
            for t in [0, 3, 5.5, 6.5, 6.6, 8.5, 11.5, 12.5, 14.9, 15.0,
                      15.2, 15.4, 15.5, 39.0, 39.4, 39.5, 40.5, 40.6,
                      43.5, 44.0, 44.4, 44.5, 50.0, 50.5, 50.9, 51.0, 59.0, 59.1]:
                clock.now = t
                self.pending.pop(0)()
            self.replay()
            clock.now = 59.15
            self.pending.pop(0)()

    root = Widgets()
    root.pending = []
    clock = SimpleNamespace(now=0)
    monkeypatch.setattr(tk, 'Tk', lambda: root)
    for name in ['Canvas', 'Frame', 'Label', 'Text', 'Button']:
        monkeypatch.setattr(tk, name, Widgets)
    monkeypatch.setattr(demo.time, 'monotonic', lambda: clock.now)
    monkeypatch.setattr(ImageTk, 'PhotoImage', lambda image: None)
    samples = []
    original = demo.ScriptRunner._sample
    def sample(runner, t):
        m = original(runner, t)
        samples.append((t, m, core.fsm.state.label))
        return m
    monkeypatch.setattr(demo.ScriptRunner, '_sample', sample)
    trace = demo.run_window(core)
    assert any(m['stage'] == 'blend' and m['transitioning'] for _, m, _ in samples)
    assert any(state == 'LISTENING' for _, _, state in samples)
    assert any(m['display_state'] == 'SPEAKING' for _, m, _ in samples)
    assert samples[-1][1]['display_state'] == 'IDLE'
    assert len(trace.samples) == 1 and not trace.errors
