"""A cache-only deployment must never start synthesis, even for invalid cache."""
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer
from tools.selected_voice_service import VoiceWorker


class CachedVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        voice = self.root / 'voice'
        voice.mkdir()
        reference = voice / 'reference.wav'
        self.write_wav(reference)
        (voice / 'selection.json').write_text(json.dumps({
            'reference_audio': 'reference.wav', 'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
            'reference_text': 'test reference'}))
        (voice / 'base_model_verification.json').write_text(json.dumps({'revision': 'test-version'}))
        self.factory = patch('tools.selected_voice_service.SelectedVoiceSynthesizer',
                             side_effect=lambda cache, model_path=None: SelectedVoiceSynthesizer(cache, model_path, voice))
        self.factory.start()
        self.worker = VoiceWorker(self.root, cached_only=True)

    def tearDown(self):
        self.worker.close()
        self.factory.stop()
        self.temp.cleanup()

    @staticmethod
    def write_wav(path, rate=24000):
        with wave.open(str(path), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(b'\x01\x00' * 240)

    def cache(self, text='cached test', rate=24000):
        key, identity = self.worker.synth.identity(text)
        directory = self.root / 'cache'
        wav = directory / (key + '.wav')
        self.write_wav(wav, rate)
        record = directory / (key + '.json')
        record.write_text(json.dumps({'key': key, 'identity': identity, 'duration_seconds': .01,
                                     'generation_seconds': 0, 'sha256': hashlib.sha256(wav.read_bytes()).hexdigest()}))
        return wav, record

    def assert_synthesis_blocked(self, text):
        with patch('tools.selected_voice_service.subprocess.Popen', side_effect=AssertionError('Unexpected process')):
            with patch.object(self.worker.synth, 'load', side_effect=AssertionError('Unexpected model load')):
                with self.assertRaisesRegex(RuntimeError, '仅缓存播放'):
                    self.worker.generate(text)
        self.assertIsNone(self.worker.process)
        self.assertIsNone(self.worker.synth.model)

    def test_valid_cache_plays_without_model_or_worker(self):
        wav, _ = self.cache()
        with patch('tools.selected_voice_service.subprocess.Popen', side_effect=AssertionError('Unexpected process')):
            result = self.worker.generate('cached test')
        self.assertEqual(Path(result['path']), wav)
        self.assertTrue(result['cache_hit'])
        self.assertIsNone(self.worker.synth.model)

    def test_cache_miss_never_starts_synthesis(self):
        self.assert_synthesis_blocked('not generated')

    def test_changed_wav_never_starts_synthesis(self):
        wav, _ = self.cache()
        wav.write_bytes(wav.read_bytes() + b'changed')
        self.assert_synthesis_blocked('cached test')

    def test_wrong_audio_format_never_starts_synthesis(self):
        self.cache(rate=16000)
        self.assert_synthesis_blocked('cached test')

    def test_changed_voice_identity_never_starts_synthesis(self):
        _, record = self.cache()
        data = json.loads(record.read_text())
        data['identity']['reference_sha256'] = 'wrong'
        record.write_text(json.dumps(data))
        self.assert_synthesis_blocked('cached test')

    def test_default_mode_still_accepts_valid_cache(self):
        self.cache()
        normal = VoiceWorker(self.root)
        self.assertFalse(normal.cached_only)
        self.assertTrue(normal.generate('cached test')['cache_hit'])
        normal.close()

    def test_existing_zero_dependency_audio_exports_still_work(self):
        audio = importlib.import_module('board.runtime.audio')
        style = importlib.import_module('board.runtime.audio.tts_style')
        self.assertIn('EnergyVad', dir(audio))
        self.assertIs(audio.TtsStyle, style.TtsStyle)


if __name__ == '__main__':
    unittest.main()
