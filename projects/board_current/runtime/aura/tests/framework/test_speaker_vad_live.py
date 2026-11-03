"""Optional installed-VAD integration; derived public speech is not enrollment."""
import importlib.util
import os
from pathlib import Path
import struct
import unittest
import wave

from common.speaker_identity import voiced_pcm


@unittest.skipUnless(importlib.util.find_spec('webrtcvad'), 'Requires independent speaker runtime')
class SpeakerVadTests(unittest.TestCase):
    def test_constant_signal_is_not_enough_speech(self):
        with self.assertRaises(ValueError):
            voiced_pcm(struct.pack('<h',1000)*48000)

    @unittest.skipUnless(os.environ.get('AURA_PUBLIC_SPEAKER_SAMPLES'), 'Requires explicit public sample directory')
    def test_concatenated_public_sentences(self):
        raw = []
        for name in ('spk1_snt1.wav','spk1_snt2.wav'):
            with wave.open(str(Path(os.environ['AURA_PUBLIC_SPEAKER_SAMPLES'])/name)) as audio:
                raw.append(audio.readframes(audio.getnframes()))
        trimmed,quality = voiced_pcm(b''.join(raw))
        self.assertGreaterEqual(quality['vad_speech_seconds'],2.5)
        self.assertLessEqual(len(trimmed),sum(map(len,raw)))


if __name__ == '__main__': unittest.main()
