"""Fake live object contracts only; no audio, ASR, devices, DB or network."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE/'after/aura/tools/production_business_ui.py'
spec = importlib.util.spec_from_file_location('safe_capture_business_ui', SOURCE)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)
PRIVATE = 'private-transcript-voice-identity-sentinel'


class Label:
    def __init__(self): self.text = ''; self.editable = self.sensitive = True
    def set_text(self, value): self.text = value
    def set_editable(self, value): self.editable = value
    def set_sensitive(self, value): self.sensitive = value


class Capture:
    def __init__(self, snapshot): self.value = snapshot; self.calls = 0
    def snapshot(self): self.calls += 1; return self.value
    def start(self): raise AssertionError('Device action forbidden')
    def stop(self): raise AssertionError('Device action forbidden')
    def read(self): raise AssertionError('PCM read forbidden')
    def take(self): raise AssertionError('Audio export forbidden')


def stage(error='', queue_error=''):
    capture = Capture(dict(state='CANCELLED', error=error, sample_count=0,
        input_ready=False, speech_active=False,
        input_queue=dict(error=queue_error, capacity_frames=8, peak_frames=8,
            frames_read=21, frames_delivered=12, source_read_max_ms=20.1,
            queue_max_ms=181.2, reader_alive=False, pcm=PRIVATE, transcript=PRIVATE),
        audio_frontend=dict(error='', frames=12, processed_samples=3840,
            last_roundtrip_ms=42.5, max_roundtrip_ms=181.2, raw=PRIVATE)))
    recording = NS(capture=capture, recording_state='CANCELLED', monitor_state='COOLDOWN',
        monitor_reason='SERVICE_ERROR', monitor_enabled=True, recording_error=error,
        monitor_error=error, auto_error='', monitor_stats=dict(armed=29, speech_starts=0,
            submitted=0, entry_rejected=0, visual_stops=0, private_text=PRIVATE),
        transcription={'text': PRIVATE}, utterance=PRIVATE)
    owner = NS(recording=recording, runtime=NS(config=NS(model_host='192.168.50.1', model_port=8797)))
    result = NS(board_business=owner, mode_label=Label(), host_status_label=Label(),
        host_entry=Label(), port_entry=Label(), controls={k: Label() for k in
            ('edit_host', 'edit_port', 'connect', 'disconnect')}, footer=Label(), toast_until=0)
    return result


class CaptureDiagnosticsTests(unittest.TestCase):
    def check_no_private(self, result):
        raw = json.dumps(result, ensure_ascii=False, allow_nan=False)
        self.assertNotIn(PRIVATE, raw)
        self.assertNotIn('operation_failed', raw)

    def test_live_capture_error_survives_presentation_mask_as_static_code(self):
        current = stage('pcm_input_queue_overflow: '+PRIVATE, 'pcm_input_queue_overflow')
        state = {'local_transcription': {'state': 'CANCELLED', 'error': 'operation_failed'}}
        ui.project_business_ui(current, state)
        diagnostic = state['safe_capture_diagnostics']
        self.assertEqual(diagnostic['error_code'], 'pcm_input_queue_overflow')
        self.assertEqual(diagnostic['error_source'], 'input_queue')
        self.assertEqual(diagnostic['input_queue']['capacity_frames'], 8)
        self.assertEqual(diagnostic['input_queue']['peak_frames'], 8)
        self.assertEqual(diagnostic['input_queue']['frames_read'], 21)
        self.assertEqual(diagnostic['input_queue']['frames_delivered'], 12)
        self.assertEqual(diagnostic['audio_frontend']['frames'], 12)
        self.assertEqual(diagnostic['counters']['armed'], 29)
        self.assertEqual(current.board_business.recording.capture.calls, 1)
        self.check_no_private(diagnostic)
        self.check_no_private([current.host_status_label.text, current.footer.text])
        self.assertFalse(current.host_entry.editable)
        self.assertFalse(current.controls['connect'].sensitive)

    def test_known_errors_classify_without_forwarding_suffix(self):
        for error, code in (
            ('pcm_input_truncated_frame: '+PRIVATE, 'pcm_input_truncated_frame'),
            ('pcm_input_read_failed: '+PRIVATE, 'pcm_input_read_failed'),
            ('MCP01 capture is already owned by another process: '+PRIVATE, 'capture_device_busy'),
            ('arecord failed with exit code 1: '+PRIVATE, 'arecord_failed'),
            ('Recording is truncated or shorter than 100 ms: '+PRIVATE, 'capture_truncated'),
            ('Board frontend is busy: '+PRIVATE, 'frontend_error'),
            (PRIVATE, 'capture_unknown_error')):
            with self.subTest(code=code):
                result = ui.safe_capture_diagnostics(stage(error))
                self.assertEqual(result['error_code'], code)
                self.check_no_private(result)

    def test_frontend_error_and_latency_are_whitelisted(self):
        current = stage(PRIVATE)
        current.board_business.recording.capture.value['audio_frontend']['error'] = PRIVATE
        result = ui.safe_capture_diagnostics(current)
        self.assertEqual(result['error_code'], 'frontend_error')
        self.assertEqual(result['audio_frontend']['last_roundtrip_ms'], 42.5)
        self.assertEqual(result['audio_frontend']['max_roundtrip_ms'], 181.2)
        self.check_no_private(result)

    def test_unknown_exception_is_never_stringified_or_archived(self):
        class PrivateException(Exception):
            def __str__(self): raise AssertionError('Must not stringify unknown exception')
        current = stage(PrivateException(PRIVATE))
        result = ui.safe_capture_diagnostics(current)
        self.assertEqual(result['error_code'], 'capture_unknown_error')
        self.check_no_private(result)
        class FailedSnapshot:
            def snapshot(self): raise PrivateException(PRIVATE)
        current.board_business.recording.capture = FailedSnapshot()
        result = ui.safe_capture_diagnostics(current)
        self.assertEqual(result['error_code'], 'capture_snapshot_failed')
        self.check_no_private(result)

    def test_corrupt_enums_and_numeric_strings_never_echo(self):
        current = stage('')
        recording = current.board_business.recording
        recording.monitor_state = recording.monitor_reason = PRIVATE
        recording.monitor_stats['armed'] = PRIVATE
        value = recording.capture.value
        value['state'] = PRIVATE
        value['input_queue'].update(peak_frames=float('nan'), frames_read=float('inf'),
            frames_delivered=10**1000, queue_mean_ms=PRIVATE, closed=PRIVATE)
        value['audio_frontend']['last_roundtrip_ms'] = PRIVATE
        result = ui.safe_capture_diagnostics(current)
        self.assertEqual(result['monitor_state'], 'UNKNOWN')
        self.assertIsNone(result['microphone_open'])
        self.assertNotIn('armed', result['counters'])
        self.assertNotIn('frames_read', result['input_queue'])
        self.check_no_private(result)

    def test_paused_and_real_recording_states_are_not_readiness_claims(self):
        current = stage('')
        rec = current.board_business.recording
        rec.monitor_enabled = False; rec.monitor_state = 'PAUSED'; rec.monitor_reason = ''
        result = ui.safe_capture_diagnostics(current)
        self.assertEqual(result['error_code'], 'none')
        self.assertEqual(result['status_text'], '聆听已暂停')
        rec.monitor_enabled = True; rec.monitor_state = 'WAITING_WAKE'
        rec.capture.value.update(state='RECORDING', input_ready=True)
        result = ui.safe_capture_diagnostics(current)
        self.assertTrue(result['microphone_open'])
        self.assertEqual(result['status_text'], '正在聆听唤醒词')

    def test_missing_binding_and_legacy_guard_remain_fail_closed(self):
        current = stage()
        current.board_business.recording = None
        result = ui.safe_capture_diagnostics(current)
        self.assertEqual(result['error_code'], 'capture_not_bound')
        with self.assertRaises(ValueError): ui.guard_legacy_configuration(current, {'type': 'asr_config'})
        self.assertIsNone(ui.project_business_ui(NS(board_business=None), {}))

    def test_python39_source_and_no_io_imports(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'), feature_version=(3, 9))
        imported = {n.names[0].name for n in tree.body if isinstance(n, ast.Import)}
        self.assertEqual(imported, {'errno', 'math', 'time'})


if __name__ == '__main__': unittest.main()
