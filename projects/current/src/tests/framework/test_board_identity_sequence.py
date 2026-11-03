"""Original board face FSM plus one local stream/player receipt; no real person."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from board.runtime.board_business import LocalIdentityReplies
from common.voice_channel import ChannelState
from tests.framework.test_board_business import runtime, clip, drain
from tests.framework.test_simple_enrollment import snapshot


class Scene:
    def __init__(self, clock, *, committed=True):
        self.clock, self.committed = clock, committed
        self.view = snapshot(); self.view['board_boot_id'] = 'test-boot'
        self.view['observed_mono_ms'] = round(clock()*1000)
        self.commands, self.advances = [], 0

    @property
    def sample(self): return self.view['modules']['identity']['enrollment_sampling']

    def snapshot(self):
        self.view['observed_mono_ms'] = round(self.clock()*1000)
        return copy.deepcopy(self.view)

    def command(self, command):
        self.commands.append(copy.deepcopy(command))
        action = command['action']
        if action == 'identity_sample_start':
            self.sample.update(session_id='sample-private-sentinel', stage='collect',
                               bound_target=copy.deepcopy(command['params']['target']))
            self.view['capabilities']['identity_sample_start'] = False
        elif action == 'identity_sample_cancel':
            self.sample.update(session_id='', stage='idle')
        elif self.committed:
            self.view['modules']['identity'].update(state='KNOWN', db_version=1,
                last_operation=dict(command_id=command['command_id'], action=action,
                                    state='COMMITTED', db_version=1, detail='saved'))
        return dict(accepted=True, command_id=command['command_id'])

    def advance(self, seconds):
        self.advances += 1; self.clock.now += seconds
        self.sample['stage'] = ('left', 'right', 'validate', 'ready')[min(self.advances-1, 3)]
        if self.sample['stage'] == 'ready':
            self.sample.update(counts={'collect': 10, 'validate': 5}, total=15)
            self.view['capabilities']['identity_enroll'] = True


def setup(tmp_path, *, committed=True):
    bundle, clock, timeline, client, capture = runtime(tmp_path)
    scene = Scene(clock, committed=committed)
    handler = LocalIdentityReplies('test-boot', scene.snapshot, scene.command,
                                   clock=clock, now_ms=lambda: round(clock()*1000))
    bundle.jobs.special_handlers.update(identity_enrollment=handler, identity_query=handler)
    bundle.jobs.select_conversation(resume=False)
    return bundle, clock, client, scene, handler


def say(bundle, scene, text):
    bundle.jobs.asr.text = text
    bundle.jobs.capture_owners = {'clip-1': scene.snapshot()}
    meta = bundle.jobs.submit(clip()); bundle.jobs.run_next(); values = drain(bundle.jobs)
    return meta, values


def ack(bundle, meta, values):
    complete = next(item['network_complete'] for item in values if 'network_complete' in item)
    bundle.jobs.acknowledge(meta, complete); bundle.jobs.drain_actions()
    return complete


def begin(bundle, scene):
    meta, values = say(bundle, scene, '帮我登记身份，我叫小林')
    assert '称呼是小林' in next(v['channel_event']['text'] for v in values
                                if v.get('channel_event', {}).get('kind') == 'text')
    ack(bundle, meta, values)
    assert not scene.commands


def test_original_guide_plays_each_phase_then_full_ack_after_committed_receipt(tmp_path, monkeypatch):
    bundle, clock, client, scene, handler = setup(tmp_path)
    begin(bundle, scene)
    early = []
    def advance(seconds):
        early.append(any(v.get('channel_event', {}).get('kind') == 'audio' for v in bundle.jobs.progress))
        owner, token = bundle.jobs._stream_clock
        assert bundle.jobs.playback_clock(owner, playback_token=token, position_seconds=.05)['audio_sample'] == 1200
        scene.advance(seconds)
    monkeypatch.setattr('board.identity.voice_enrollment.time.sleep', advance)
    meta, values = say(bundle, scene, '确认登记')
    state = ChannelState(meta)
    for item in values:
        if 'channel_event' in item: state.accept(item['channel_event'], item['pcm'])
    assert state.ended and state.samples > 0
    # The accepted upfront-consent FSM intentionally suppresses extra left/
    # right speech, but retains the held-out validation cue and final result.
    assert '稍停几秒' in state.text and scene.advances == 4 and all(early)
    assert state.text.endswith('登记成功啦，以后我会尝试认出你。')
    assert [c['action'] for c in scene.commands].count('identity_enroll') == 1
    assert all(kind == 'tts' for kind, _ in client.calls)
    assert 'sample-private-sentinel' not in repr(client.calls)
    # The scene changes happen while the same stream remains pending; all
    # chunks get one final receipt, no per-stage fabricated played ACK.
    assert bundle.jobs.last_ack['request_id'] != meta['request_id']
    complete = ack(bundle, meta, values)
    assert complete['sample_count'] == state.samples and bundle.jobs.last_ack['committed']
    assert handler.public()['active'] is False and bundle.idle()
    bundle.close()


def test_uncertain_face_commit_cannot_emit_a_success_cue(tmp_path, monkeypatch):
    bundle, clock, client, scene, _ = setup(tmp_path, committed=False)
    begin(bundle, scene)
    monkeypatch.setattr('board.identity.voice_enrollment.time.sleep', scene.advance)
    meta, values = say(bundle, scene, '确认登记')
    text = ''.join(v['channel_event']['text'] for v in values if v.get('channel_event', {}).get('kind') == 'text')
    assert '登记成功啦' not in text and '没有确认登记成功' in text
    assert any(c['action'] == 'identity_enroll' for c in scene.commands)
    ack(bundle, meta, values)
    bundle.close()


def test_guide_uses_original_turn_deadline_and_never_gets_an_unbounded_new_budget(tmp_path, monkeypatch):
    bundle, clock, client, scene, _ = setup(tmp_path)
    begin(bundle, scene)
    def expire(seconds): clock.now += 121.
    monkeypatch.setattr('board.identity.voice_enrollment.time.sleep', expire)
    meta, values = say(bundle, scene, '确认登记')
    assert values[-1]['error'] == 'TimeoutError'
    assert not any('network_complete' in value for value in values)
    assert not any(c['action'] == 'identity_enroll' for c in scene.commands)
    assert bundle.jobs.last_ack['request_id'] != meta['request_id']
    bundle.jobs.drain_actions(); bundle.close()


def test_new_capture_cancels_guide_and_no_complete_receipt_can_survive(tmp_path, monkeypatch):
    bundle, clock, client, scene, _ = setup(tmp_path)
    begin(bundle, scene)
    def cancel(seconds): bundle.jobs.cancel()
    monkeypatch.setattr('board.identity.voice_enrollment.time.sleep', cancel)
    meta, values = say(bundle, scene, '确认登记')
    assert not any('network_complete' in value for value in values)
    assert not any(c['action'] == 'identity_enroll' for c in scene.commands)
    bundle.jobs.drain_actions()
    assert bundle.jobs.last_ack['request_id'] != meta['request_id']
    bundle.close()


def test_scope_clear_stops_sampling_success_and_late_cues(tmp_path, monkeypatch):
    bundle, clock, client, scene, _ = setup(tmp_path)
    begin(bundle, scene)
    scope = {'kind': 'conversation', 'id': bundle.jobs.conversation_selection.active}
    def clear(seconds):
        bundle.store.clear(scope)
        scene.advance(seconds)
    monkeypatch.setattr('board.identity.voice_enrollment.time.sleep', clear)
    meta, values = say(bundle, scene, '确认登记')
    assert not any('network_complete' in value for value in values)
    assert not any(c['action'] == 'identity_enroll' for c in scene.commands)
    bundle.jobs.drain_actions()
    assert bundle.jobs.last_ack['request_id'] != meta['request_id']
    bundle.close()
