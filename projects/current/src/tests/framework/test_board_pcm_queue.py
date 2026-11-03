"""Actual raw-pump/capture consumer contracts; no device/model is opened."""
import io
import signal
import threading
import time
from types import SimpleNamespace

import pytest

from board.runtime.audio.board_pcm_queue import (BoundedPcmCaptureMixin,
    BoundedPcmInput, PcmInputError)


class ControlledStream:
    def __init__(self):
        self.condition = threading.Condition()
        self.frames = []
        self.stopped = False
        self.called = threading.Event()

    def append(self, frame):
        with self.condition:
            self.frames.append(frame)
            self.condition.notify_all()

    def stop(self):
        with self.condition:
            self.stopped = True
            self.condition.notify_all()

    def read(self, size):
        assert size == 640
        self.called.set()
        with self.condition:
            while not self.frames and not self.stopped:
                self.condition.wait(.02)
            return self.frames.pop(0) if self.frames else b''


def eventually(check, timeout=1):
    until = time.monotonic()+timeout
    while not check() and time.monotonic()<until:
        time.sleep(.002)
    assert check()


def test_exact_frames_order_and_eof_without_model_in_producer():
    source = ControlledStream()
    pump = BoundedPcmInput(source, stop_source=source.stop, max_frames=2).start()
    try:
        expected = [bytes([index])*640 for index in range(1, 9)]
        actual = []
        for frame in expected:
            source.append(frame)
            actual.append(pump.read(640))
        source.stop()
        assert pump.read() == b''
        pump.finish()
        assert actual == expected
        stats = pump.public()
        assert stats['frames_read'] == stats['frames_delivered'] == 8
        assert stats['peak_frames'] <= 2 and not stats['reader_alive'] and not stats['error']
    finally:
        pump.close()


def test_slow_consumer_cannot_make_queue_unbounded_or_silently_drop():
    source = io.BytesIO(b''.join(bytes([i])*640 for i in range(1, 8)))
    pump = BoundedPcmInput(source, stop_source=lambda: None, max_frames=2).start()
    eventually(lambda: pump.public()['error'] != '')
    with pytest.raises(PcmInputError, match='pcm_input_queue_overflow'):
        pump.read()
    with pytest.raises(PcmInputError, match='pcm_input_queue_overflow'):
        pump.finish()
    stats = pump.public()
    assert stats['peak_frames'] == 2 and stats['queued_frames'] == 0
    assert stats['frames_delivered'] == 0 and stats['frames_read'] == 3
    assert not stats['reader_alive']


@pytest.mark.parametrize('bad', [b'\0'*2, b'\0'*642, bytearray(640), None])
def test_truncated_or_invalid_source_frame_fails_whole_capture(bad):
    pump = BoundedPcmInput(SimpleNamespace(read=lambda size: bad), stop_source=lambda: None).start()
    try:
        with pytest.raises(PcmInputError, match='pcm_input_truncated_frame'):
            pump.read()
        assert pump.public()['frames_delivered'] == 0
    finally:
        pump.close()


def test_cancel_unblocks_reader_and_waiting_consumer_without_pipe_close():
    source, errors = ControlledStream(), []
    pump = BoundedPcmInput(source, stop_source=source.stop).start()
    def consume():
        try:
            pump.read()
        except BaseException as exc:
            errors.append(exc)
    consumer = threading.Thread(target=consume)
    consumer.start()
    assert source.called.wait(1)
    began = time.monotonic()
    pump.cancel()
    assert pump.close()
    consumer.join(.4)
    assert not consumer.is_alive() and time.monotonic()-began<.4
    assert len(errors) == 1 and isinstance(errors[0], InterruptedError)
    assert pump.public()['cancelled'] and not pump.public()['reader_alive']


def test_uncooperative_input_cannot_hang_cleanup_or_be_accepted():
    unblock = threading.Event()
    entered = threading.Event()
    def read(_):
        entered.set()
        unblock.wait(3)
        return b''
    pump = BoundedPcmInput(SimpleNamespace(read=read), stop_source=lambda: None, join_timeout=.05).start()
    try:
        assert entered.wait(1)
        began = time.monotonic()
        with pytest.raises(PcmInputError, match='pcm_input_reader_not_stopped'):
            pump.finish()
        assert time.monotonic()-began < .3 and pump.public()['reader_alive']
    finally:
        unblock.set()
        assert pump.close()


def test_overflow_while_final_endpoint_decision_runs_rejects_complete_result():
    source = ControlledStream()
    pump = BoundedPcmInput(source, stop_source=source.stop, max_frames=1).start()
    try:
        source.append(b'\0'*640)
        assert pump.read() == b'\0'*640
        # A consumer's final native decision may still be running here.
        source.append(b'1'*640)
        source.append(b'2'*640)
        eventually(lambda: pump.public()['error'] != '')
        with pytest.raises(PcmInputError, match='pcm_input_queue_overflow'):
            pump.finish()
    finally:
        pump.close()


@pytest.mark.parametrize('kind', ['automatic', 'barge'])
def test_actual_capture_read_loop_uses_raw_pump_and_original_endpoint(kind):
    from board.runtime.audio.automatic_capture import AutomaticMcp01Capture
    from board.runtime.audio.board_capture import BoardAutomaticCapture, BoardBargeCapture
    # BoardAutomaticCapture now uses the real mixin after runtime integration.
    assert issubclass(BoardAutomaticCapture, BoundedPcmCaptureMixin)
    assert AutomaticMcp01Capture in BoardAutomaticCapture.__mro__
    source = ControlledStream()
    process = SimpleNamespace(stdout=source)
    calls, decisions, failures = [], [], []
    class Gate:
        def __call__(self, frame):
            assert threading.current_thread().name == 'probe-original-consumer'
            decisions.append(True)
            return len(decisions) <= 12
        def close(self):
            calls.append('gate_closed')
        def public(self):
            return {'enabled': True}
    gate = Gate()
    if kind == 'automatic':
        capture = BoardAutomaticCapture(lambda: False, frontend_factory=lambda: gate,
            process_factory=lambda *a, **k: pytest.fail('No microphone process may start'))
        capture.endpoint = capture._endpoint()
    else:
        assert issubclass(BoardBargeCapture, BoundedPcmCaptureMixin)
        capture = BoardBargeCapture(SimpleNamespace(), frontend_factory=lambda: gate,
            process_factory=lambda *a, **k: pytest.fail('No microphone process may start'))
        capture.echo = SimpleNamespace(process=lambda raw: raw, healthy=lambda: True,
                                       close=lambda: calls.append('echo_closed'), reference_gaps=0)
        capture._new_endpoint()
        assert capture.endpoint.vad.config.min_speech_ms == 240
    capture._signal = lambda signum: (calls.append(signum), source.stop())
    results = []
    def consume():
        try:
            results.append(capture._read_pcm(process))
        except BaseException as exc:
            failures.append(exc)
    consumer = threading.Thread(target=consume, name='probe-original-consumer')
    consumer.start()
    stream = b''.join(bytes([index])*640 for index in range(1, 61))
    for offset in range(0, len(stream), 640):
        if source.stopped:
            break
        source.append(stream[offset:offset+640])
        time.sleep(.001)
    consumer.join(2)
    if capture._timer is not None:
        capture._timer.cancel()
    assert not consumer.is_alive() and not failures, failures
    assert len(results) == 1 and results[0]
    result = results[0]
    offset = capture.endpoint.start_sample*2
    assert result == stream[offset:offset+len(result)]
    assert capture.endpoint.speech_samples == len(result)//2
    assert capture._board_pcm_input.public()['error'] == ''
    assert capture._board_pcm_input.public()['frames_read'] > 0
    assert signal.SIGINT in calls and 'gate_closed' in calls
    assert not capture._board_pcm_input.public()['reader_alive']


def test_input_read_failure_is_explicit_and_not_empty_speech():
    def read(_):
        raise OSError('Synthetic source failure')
    pump = BoundedPcmInput(SimpleNamespace(read=read), stop_source=lambda: None).start()
    try:
        with pytest.raises(PcmInputError, match='pcm_input_read_failed'):
            pump.read()
        assert pump.public()['frames_delivered'] == 0
    finally:
        assert pump.close()
