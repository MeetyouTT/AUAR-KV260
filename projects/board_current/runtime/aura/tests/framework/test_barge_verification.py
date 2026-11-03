"""Energy alone cannot cancel playback; partial ASR is not conversation history."""
import io
from types import SimpleNamespace
import time

import pytest

from board.runtime.audio.barge_verify import classify_interruption, InterruptionVerifier
from tests.framework import test_voice_barge_in as fixtures
from tests.framework.test_automatic_conversation import frames
from tools.barge_in_capture import BargeInCapture


@pytest.mark.parametrize('heard', ['我就安安静静待在你手边', '安安静静待在你手边陪着你', '我就安静待在你手边'])
def test_partial_and_slightly_misrecognized_own_speech_is_echo(heard):
    assert classify_interruption(heard, '我就安安静静待在你手边，陪着你发呆或者听你碎碎念呀。') == 'echo'


@pytest.mark.parametrize('heard', ['先停一下，你叫什么名字', '等一下', '停', '我们明天的计划是什么'])
def test_distinct_new_questions_and_stop_commands_are_preserved(heard):
    assert classify_interruption(heard, '小狐狸把月亮偷来当灯笼，走着走着就迷路啦。') == 'new_speech'


def test_empty_filler_or_absent_reference_cannot_authorize_interrupt():
    for heard, spoken in [('', '你好呀'), ('嗯嗯', '你好呀'), ('谢谢观看', '你好呀'), ('先停一下', '')]:
        assert classify_interruption(heard, spoken) == 'unclear'


def test_verifier_uses_bounded_plain_asr_and_never_returns_transcript():
    calls = []
    def transport(config, meta, pcm, timeout):
        calls.append((config, meta, pcm, timeout))
        return {'text': '先停一下，你叫什么名字'}
    verifier = InterruptionVerifier(lambda: {'host':'192.168.50.1','port':8792}, 'boot', transport=transport)
    try:
        assert verifier.submit(b'\x12\x34'*12800, '小狐狸把月亮偷来当灯笼。')
        assert not verifier.submit(b'\x12\x34'*12800, '不允许第二个并发请求')
        verifier.future.result(timeout=2)
        result = verifier.poll()
        assert result['decision'] == 'new_speech' and 'text' not in result
        assert len(calls) == 1 and calls[0][3] == 1.5
        assert calls[0][1]['sample_count'] == 12800 and 'conversation' not in calls[0][1]
        assert verifier.poll() is None
    finally:
        verifier.close()
    assert not verifier.submit(bytes(6400), '已关闭')


class VerifierStub:
    def __init__(self, decision):
        self.decision = decision
        self.pending = False
        self.calls = []
        self.closed = False
    def submit(self, pcm, spoken):
        self.pending = True
        self.calls.append((pcm, spoken))
        return True
    def poll(self):
        if not self.pending:
            return None
        self.pending = False
        return {'decision': self.decision}
    def close(self): self.closed = True


def capture(verifier):
    cap = BargeInCapture(SimpleNamespace(), verifier=verifier, spoken_text=lambda:'我正在讲一个小故事。')
    cap._capture_timer()
    cap.echo = fixtures.EchoStub()
    return cap


@pytest.mark.parametrize('decision', ['echo', 'unclear', 'unavailable'])
def test_residual_voice_without_new_speech_never_calls_interrupt(decision):
    verifier = VerifierStub(decision)
    cap = capture(verifier)
    callbacks = []
    cap.on_speech_start = lambda: callbacks.append(True)
    try:
        with pytest.raises(RuntimeError, match='ended unexpectedly'):
            cap._read_pcm(SimpleNamespace(stdout=io.BytesIO(frames(30)+frames(70,True)+frames(40))))
        assert not callbacks and verifier.calls
        assert cap.confirm_stats['confirmed'] == 0
        assert verifier.closed
    finally:
        cap.close()


def test_confirmed_new_speech_keeps_original_preroll_and_entire_utterance():
    verifier = VerifierStub('new_speech')
    cap = capture(verifier)
    callbacks = []
    cap.on_speech_start = lambda: callbacks.append(cap.endpoint.total_samples)
    raw = frames(30)+frames(40,True)+frames(35)
    try:
        result = cap._read_pcm(SimpleNamespace(stdout=io.BytesIO(raw)))
        assert len(callbacks) == 1 and callbacks[0] > 42*320
        assert result == raw[20*640:]
        assert cap.confirm_stats['confirmed'] == 1
        assert len(verifier.calls) == 1
    finally:
        cap.close()


def test_pending_echo_candidate_cannot_bypass_verification_at_ack_handoff():
    now, source, tx, inner, owner, captures = fixtures.setup()
    owner.early_listen = True
    try:
        fixtures.generating(owner, inner)
        cap = captures[0]
        original = cap.snapshot
        cap.snapshot = lambda: dict(original(), speech_verification={'candidate': True, 'pending': True})
        inner.state.update(phase='IDLE', playing=False)
        tx.pending = False
        inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'}, {}))
        owner.tick()
        tx.last_ack = {'request_id':'req-1','committed':True}
        now[0] += .6
        source[0] = fixtures.view(2200, 3)
        owner.tick()
        assert owner.barge_capture is cap and owner.tail_handoffs == 0
        assert owner.auto_state == 'CONFIRMING_INTERRUPTION'
    finally:
        owner.close()


def test_production_factory_binds_current_asr_and_reply_without_opening_microphone():
    from tools.barge_in_recording import BargeInRecordingController
    from unittest.mock import patch
    config = {'enabled': True, 'host': '192.168.50.1', 'port': 8792, 'timeout_ms': 30000}
    tx = fixtures.Tx()
    tx.config = config
    inner = fixtures.FakeController()
    inner.output = object()
    inner.reply = '我是汐蓝，我正在给你讲故事。'
    owner = None
    verifier = None
    try:
        with patch('tools.barge_in_capture.BargeInCapture') as factory:
            owner = BargeInRecordingController(inner, transcriber=tx, boot_id='boot',
                attention_provider=lambda: None, auto_capture_factory=fixtures.FakeCapture)
            owner.barge_factory()
            verifier = factory.call_args.kwargs['verifier']
            assert verifier.boot_id == 'boot' and verifier.config_provider() == config
            assert factory.call_args.kwargs['spoken_text']() == inner.reply
    finally:
        if verifier: verifier.close()
        if owner: owner.close()
