"""Exercise real worker, ownership and named matcher with synthetic short voices."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import sys
import threading
import time
from types import SimpleNamespace

import pytest

TASK = Path(__file__).resolve().parent
RUNTIME = TASK / 'candidate_runtime'
os.environ['AURA_SPEAKER_RUNTIME'] = str(RUNTIME)
sys.path.insert(0, str(RUNTIME))
spec = importlib.util.spec_from_file_location('short_voice_original_harness',
    TASK.parent / '2026-11-02_voice_speaker_recognition/tests/test_per_utterance_speaker.py')
original = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = original
spec.loader.exec_module(original)
from board.runtime.board_speaker_business import ordinary_voice_segment
from common.speaker_identity import voiced_pcm


class Vad:
    enabled = True

    def __init__(self, mode):
        assert mode == 2

    def is_speech(self, frame, rate):
        assert rate == 16000 and len(frame) == 960
        return self.enabled


@pytest.fixture
def h(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'webrtcvad', SimpleNamespace(Vad=Vad))
    monkeypatch.setattr(Vad, 'enabled', True)
    value = original.Harness(tmp_path / 'short-synthetic-speakers')
    value.service.quality = voiced_pcm
    try:
        yield value
    finally:
        value.close()


def capture(h, marker, seconds, *, submit=True):
    h.sequence += 1
    count = round(seconds * 16000)
    pcm = struct.pack('<hh', marker, h.sequence) + b'\x01\x00' * (count - 2)
    meta = dict(protocol='aura-asr-1', board_boot_id='synthetic-boot', session_id='synthetic-session',
        request_id='short-request-' + str(h.sequence), generation=h.sequence,
        capture_id='short-capture-' + str(h.sequence), sample_count=count,
        pcm_sha256=hashlib.sha256(pcm).hexdigest(), budget_ms=120000)
    cancel = threading.Event()
    call = meta, pcm, cancel, h.cid
    if submit:
        h.service.submit_analysis(meta, pcm, h.cid, cancel_event=cancel, deadline=time.monotonic() + 4)
    return call


def say(h, marker, seconds):
    call = capture(h, marker, seconds)
    h.settled()
    return h.hint(call)


def test_252_second_capture_names_voice_without_a_face_and_encodes_once(h):
    assert say(h, 1, 2.52)['display_name'] == '测试甲'
    assert h.encoder.calls == 1
    view = h.service.public()['conversation_address']
    assert view['phase'] == 'MATCHED' and view['current_capture_match']
    assert view['speech_quality']['voiced_ms'] == 2520
    assert view['speech_quality']['minimum_voiced_ms'] == 1500
    assert view['personal_memory_allowed'] is False
    assert not h.service.hub.progressive_speaker.provisional.streaks
    assert not h.service.hub.progressive_speaker.provisional.results


def test_short_a_b_a_switches_on_each_current_capture(h):
    for marker, name in ((1, '测试甲'), (2, '测试乙'), (1, '测试甲')):
        assert say(h, marker, 1.8)['display_name'] == name
    assert h.encoder.calls == 3


@pytest.mark.parametrize('marker', [3, 4], ids=['unknown', 'ambiguous'])
def test_unmatched_short_voice_clears_previous_name(h, marker):
    assert say(h, 1, 3.3)['display_name'] == '测试甲'
    assert say(h, marker, 2.1) is None
    assert h.service.public()['conversation_address']['phase'] == 'NO_MATCH'
    assert not h.service.public()['conversation_address']['current_capture_match']


def test_less_than_15_seconds_never_encodes_or_inherits_name(h):
    assert say(h, 1, 3.3)['display_name'] == '测试甲'
    before = h.encoder.calls
    assert say(h, 1, 1.2) is None
    assert h.encoder.calls == before
    assert h.service.public()['conversation_address']['speech_quality']['reason'] == 'CAPTURE_TOO_SHORT'


def test_silence_does_not_match_even_with_sufficient_total_duration(h, monkeypatch):
    monkeypatch.setattr(Vad, 'enabled', False)
    assert say(h, 1, 2.52) is None
    assert h.encoder.calls == 0
    assert h.service.public()['conversation_address']['speech_quality']['voiced_ms'] == 0


def test_normal_long_capture_still_encodes_only_once(h):
    assert say(h, 2, 3.3)['display_name'] == '测试乙'
    assert h.encoder.calls == 1
    assert h.service.public()['conversation_address']['speech_quality']['minimum_voiced_ms'] == 2500


def test_enrollment_control_retains_original_three_second_audio_gate(h):
    meta, pcm, cancel, cid = capture(h, 1, 2.52, submit=False)
    future, _ = h.service._submit(h.service._quality, meta, pcm, control=True, cid=cid,
        cancel_event=cancel, deadline=time.monotonic() + 3)
    with pytest.raises(ValueError, match='3–20s'):
        future.result(2)
    assert h.encoder.calls == 0


def test_active_enrollment_disables_short_naming_fallback(h):
    def active():
        h.service.hub.speaker.sessions['synthetic-registration'] = {}
    h.service.pool.submit(active).result(2)
    try:
        assert say(h, 1, 2.52) is None
        assert h.encoder.calls == 0
    finally:
        h.service.pool.submit(h.service.hub.speaker.sessions.clear).result(2)


def test_lowered_match_threshold_is_refused_for_short_naming(h):
    h.service.pool.submit(lambda: setattr(h.service.hub.speaker, 'threshold', .34)).result(2)
    assert say(h, 1, 2.52) is None
    assert h.encoder.calls == 0


def test_cancelled_short_voice_cannot_publish_a_name(h):
    h.encoder.block_kind = 1
    call = capture(h, 1, 2.52)
    assert h.encoder.entered.wait(1)
    call[2].set()
    h.encoder.release.set()
    h.settled()
    assert h.hint(call) is None


def test_old_short_voice_cannot_overwrite_a_new_speaker(h):
    h.encoder.block_kind = 1
    old = capture(h, 1, 2.52)
    assert h.encoder.entered.wait(1)
    newer = capture(h, 2, 2.1)
    h.encoder.release.set()
    h.settled()
    assert h.hint(old) is None
    assert h.hint(newer)['display_name'] == '测试乙'


def test_gallery_change_during_short_encoding_invalidates_candidate(h):
    encode = h.encoder.encode
    def changed(pcm):
        vector = encode(pcm)
        h.service.hub.speaker.store.original.delete('synthetic-person-a')
        return vector
    h.encoder.encode = changed
    assert say(h, 1, 2.52) is None


def test_synthetic_quality_failure_does_not_fall_back_to_other_quality(h):
    h.service.quality = original.quality
    assert say(h, 5, 3.3) is None
    assert h.encoder.calls == 0


@pytest.mark.parametrize('pcm', [b'\x00', b'\x00' * 640002, 'invalid'],
    ids=['odd-byte-count', 'over-limit', 'wrong-type'])
def test_short_quality_rejects_invalid_input(pcm):
    raw, details = ordinary_voice_segment(pcm)
    assert raw is None and details['reason'] == 'INVALID_AUDIO'
