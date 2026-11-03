"""Independent narrow exception-boundary counterexamples; entirely synthetic RAM."""
import hashlib
from pathlib import Path
import sys
import pytest

FIX = Path(__file__).resolve().parents[1]
EXPECTED = {
    'board/runtime/audio/board_asr.py': 'c51488ac6bd3563bc3dc42934b321e98e26cb2b58d700318765a60ca4908ef60',
    'board/runtime/audio/board_dialogue_jobs.py': '01b27ede0d8889c35fc9ac990e03538a55fecc7c6a604fb6f781bc5d54c09087'}
for relative, checksum in EXPECTED.items():
    assert hashlib.sha256((FIX / 'candidate' / relative).read_bytes()).hexdigest() == checksum
sys.path.insert(0, str(FIX))
import test_no_speech_pipeline as pipeline
assert pipeline.MODE == 'candidate'


def test_same_message_generic_value_error_keeps_generic_failure_and_reset():
    harness = pipeline.Harness()
    harness.begin()
    before = (len(harness.store.rows), len(harness.models.calls), len(harness.camera.commands))
    harness.turn(None, failure=ValueError('Board ASR returned no speech'))
    assert harness.recording.transcription['state'] == 'ERROR'
    assert harness.handler.flow.stage == 'idle' and harness.business.resets >= 1
    assert not harness.jobs.latency_metrics['entry_rejected']
    assert before == (len(harness.store.rows), len(harness.models.calls), len(harness.camera.commands))


def test_identically_named_unrelated_exception_is_not_treated_as_trusted_type():
    harness = pipeline.Harness()
    harness.begin()
    unrelated_type = type('BoardNoSpeech', (ValueError,), {})
    assert unrelated_type is not pipeline.asr_module.BoardNoSpeech
    harness.turn(None, failure=unrelated_type('synthetic nontrusted exception'))
    assert harness.recording.transcription['state'] == 'ERROR'
    assert harness.handler.flow.stage == 'idle' and harness.business.resets >= 1
    assert not harness.jobs.latency_metrics['entry_rejected']
    assert harness.camera.commands == []


def test_trusted_type_raised_after_asr_is_not_caught_as_benign_asr_blank():
    harness = pipeline.Harness()
    harness.begin()
    def failing_admission(job, raw_text):
        raise pipeline.asr_module.BoardNoSpeech('synthetic later stage failure')
    harness.jobs._admit_text = failing_admission
    harness.turn('确认登记', direct=True)
    assert harness.recording.transcription['state'] == 'ERROR'
    assert harness.handler.flow.stage == 'idle' and harness.business.resets >= 1
    assert not harness.jobs.latency_metrics['entry_rejected']
    assert harness.jobs.latency_metrics['asr_completed'] is True
    assert harness.camera.commands == []


def test_real_typed_blank_preserves_existing_consent_and_has_no_downstream_side_effects():
    harness = pipeline.Harness()
    consent = harness.begin()
    before = (len(harness.store.rows), len(harness.store.acks), len(harness.models.calls),
              len(harness.camera.commands), harness.handler.invocations, harness.business.turns)
    harness.turn(None, failure=pipeline.asr_module.BoardNoSpeech('synthetic typed blank'))
    assert harness.jobs.latency_metrics['entry_rejected'] is True
    assert harness.recording.wake_rearm and harness.handler.flow.stage == 'authorize'
    assert harness.business.resets == 0
    after_consent = (harness.handler.flow.epoch, harness.handler.flow.owner, harness.handler.flow.until,
                     harness.handler.flow.name, harness.recording.monitor_key, harness.jobs.session_id)
    assert consent == after_consent
    assert before == (len(harness.store.rows), len(harness.store.acks), len(harness.models.calls),
                      len(harness.camera.commands), harness.handler.invocations, harness.business.turns)


@pytest.mark.parametrize('raw_text', ['\n', '\t', '\r\n'])
def test_direct_protocol_control_char_only_output_preserves_original_error_boundary(raw_text):
    harness = pipeline.Harness()
    harness.begin()
    harness.turn(raw_text, direct=True)
    assert harness.recording.transcription['state'] == 'ERROR'
    assert harness.handler.flow.stage == 'idle' and harness.business.resets >= 1
    assert not harness.jobs.latency_metrics['entry_rejected']
    assert harness.jobs.latency_metrics['error_class'] == 'ValueError'
    assert harness.camera.commands == []
