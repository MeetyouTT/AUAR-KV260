"""Capture ownership, payload, cancellation and subprocess cleanup boundaries."""
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from board.runtime.audio.capture import FORMAT, Mcp01Capture
from board.runtime.media_session import MediaSessionManager


class FakeProcess:
    def __init__(self, pcm=b'\x01\x00'*1600, rc=0):
        self.stdout = io.BytesIO(pcm)
        self.rc = rc
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = self.rc
        return self.rc

    def send_signal(self, signum):
        self.returncode = self.rc

    def kill(self):
        self.returncode = self.rc


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lock = Path(self.temp.name)/'capture.lock'

    def capture(self, process=None, playback=lambda:False, factory=None):
        process = process or FakeProcess()
        capture = Mcp01Capture(playback, max_seconds=.2, lock_path=self.lock,
                              process_factory=factory or (lambda *args, **kwargs:process))
        self.addCleanup(capture.close)
        return capture

    def completed(self, capture):
        capture.start()
        capture._thread.join(timeout=2)
        self.assertFalse(capture._thread.is_alive())
        return capture

    def test_recording_payload_enters_existing_media_contract(self):
        calls = []
        process = FakeProcess()
        def factory(args, **kwargs):
            calls.append(args)
            return process
        capture = self.completed(self.capture(factory=factory))
        capture.stop()
        clip = capture.take()
        self.assertEqual(clip.audio.fmt, FORMAT)
        self.assertEqual(clip.audio.sample_count, 1600)
        self.assertEqual(clip.metadata()['pcm_bytes'], 3200)
        self.assertIn('hw:CARD=MCP01,DEV=0', calls[0])
        session = MediaSessionManager('test-boot', lambda:1, 15000)
        _, payload = session.begin(clip.audio, clip.pcm, None, 100)
        self.assertEqual(payload['pcm'], clip.pcm)
        self.assertEqual(capture.state, 'IDLE')
        with self.assertRaises(RuntimeError):
            capture.take()

    def test_playback_or_unknown_state_never_opens_capture(self):
        for active in (True, None, 'false'):
            capture = self.capture(playback=lambda:active,
                factory=lambda *a, **kw:self.fail('Microphone opened during playback'))
            with self.assertRaisesRegex(RuntimeError, 'Stop playback'):
                capture.start()

    def test_unreadable_playback_state_is_not_treated_as_idle(self):
        def unavailable():
            raise RuntimeError('Playback service unavailable')
        capture = self.capture(playback=unavailable)
        with self.assertRaisesRegex(RuntimeError, 'service unavailable'):
            capture.start()

    def test_cancel_discards_completed_audio_and_new_recording_changes_epoch(self):
        capture = self.completed(self.capture(factory=lambda *a, **k:FakeProcess()))
        first_epoch = capture.epoch
        capture.cancel()
        self.assertFalse(capture.snapshot()['has_result'])
        with self.assertRaises(RuntimeError):
            capture.take()
        self.completed(capture)
        self.assertEqual(capture.take().audio.audio_epoch, first_epoch+1)

    def test_pending_result_cannot_be_silently_replaced(self):
        capture = self.completed(self.capture())
        with self.assertRaisesRegex(RuntimeError, 'Consume or cancel'):
            capture.start()

    def test_bad_size_and_process_failure_do_not_publish_audio(self):
        cases = [(b'\x01\x00'*3201, 0, 'sample limit'),
                 (b'\x01\x00'*1600+b'x', 0, 'truncated'),
                 (b'\0'*100, 0, 'shorter'),
                 (b'\x01\x00'*1600, 2, 'exit code 2')]
        for pcm, rc, message in cases:
            capture = self.completed(self.capture(FakeProcess(pcm, rc)))
            self.assertEqual(capture.state, 'ERROR')
            with self.assertRaisesRegex(RuntimeError, message):
                capture.stop()
            self.assertFalse(capture.snapshot()['has_result'])

    def test_failed_process_start_releases_device_owner(self):
        def unavailable(*args, **kwargs):
            raise FileNotFoundError('arecord unavailable')
        capture = self.capture(factory=unavailable)
        with self.assertRaises(FileNotFoundError):
            capture.start()
        self.completed(self.capture()).take()

    def test_real_subprocess_stop_and_exclusive_owner(self):
        launched = threading.Event()
        def factory(args, **kwargs):
            code = "import sys,time;sys.stdout.buffer.write(b'\\x01\\x00'*3200);sys.stdout.buffer.flush();time.sleep(10)"
            process = subprocess.Popen([sys.executable, '-B', '-c', code], **kwargs)
            launched.set()
            return process
        capture = self.capture(factory=factory)
        capture.start()
        self.assertTrue(launched.wait(1))
        other = self.capture()
        with self.assertRaisesRegex(RuntimeError, 'already owned'):
            other.start()
        import time
        deadline = time.monotonic()+2
        while capture.snapshot()['sample_count'] < 2048 and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertGreaterEqual(capture.snapshot()['sample_count'], 2048)
        clip = capture.stop()
        self.assertEqual(clip.audio.sample_count, 3200)
        self.assertIsNone(capture._process)
        self.completed(other).take()

    def test_invalid_device_and_unbounded_duration_rejected(self):
        for duration in (0, 21, float('nan'), True):
            with self.assertRaises(ValueError):
                Mcp01Capture(lambda:False, max_seconds=duration)
        with self.assertRaises(ValueError):
            Mcp01Capture(lambda:False, device='hw:2,0')


if __name__ == '__main__':
    unittest.main()
