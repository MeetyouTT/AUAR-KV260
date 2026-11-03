"""Offline speaker prototype. Never binds camera tracks or conversation history."""
import math
import hashlib
import json
import sqlite3
import struct
import wave
from pathlib import Path
from contextlib import closing

from board.identity.store import IdentityStore, normalize

MODEL_FILES = {'hyperparams.yaml', 'embedding_model.ckpt', 'classifier.ckpt',
               'mean_var_norm_emb.ckpt', 'label_encoder.txt'}


def verify_model(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if set(manifest['sha256']) != MODEL_FILES:
        raise ValueError('Incomplete speaker model manifest')
    hashes = {name: hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in MODEL_FILES}
    if hashes != manifest['sha256']:
        raise ValueError('Speaker model fingerprint mismatch')
    expected = 'ecapa-voxceleb-'+hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    if manifest['model_id'] != expected:
        raise ValueError('Invalid speaker model ID')
    return expected


class SpeakerStore(IdentityStore):
    """Only opens a database carrying our separate application marker."""
    APPLICATION_ID = 0x41555350

    def __init__(self, path, model_id, dimension, threshold, ambiguity_margin, *, create=False):
        if not math.isfinite(threshold) or not math.isfinite(ambiguity_margin):
            raise ValueError('Non-finite speaker threshold')
        path = Path(path).resolve()
        if path.exists():
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as existing:
                marker = existing.execute('PRAGMA application_id').fetchone()[0]
            if marker != self.APPLICATION_ID:
                raise ValueError('Not a speaker database; refuse to change it')
        elif not create:
            raise ValueError('Speaker database does not exist')
        super().__init__(path, model_id, dimension, threshold, ambiguity_margin)
        self.db.execute('PRAGMA application_id='+str(self.APPLICATION_ID))
        self.db.commit()


def read_pcm(path):
    with wave.open(str(path), 'rb') as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth(), audio.getcomptype()) != (16000, 1, 2, 'NONE'):
            raise ValueError('Require uncompressed 16kHz mono PCM16 WAV')
        count = audio.getnframes()
        if not 3 * 16000 <= count <= 20 * 16000:
            raise ValueError('Require 3–20 seconds per recording')
        raw = audio.readframes(count)
    if len(raw) != count * 2:
        raise ValueError('Truncated recording')
    samples = struct.unpack('<%dh' % count, raw)
    # Conservative energy gate, not a VAD or proof of a single live speaker.
    active = sum(math.sqrt(sum(v*v for v in samples[i:i+320])/320) >= 150
                 for i in range(0, count-319, 320))
    if active * .02 < 2.5:
        raise ValueError('Insufficient non-silent audio')
    if sum(abs(v) >= 32760 for v in samples) / count > .01:
        raise ValueError('Clipped recording')
    return raw


def voiced_pcm(raw, minimum_seconds=2.5):
    """WebRTC VAD gate and edge trim; not overlap or spoof detection."""
    import webrtcvad
    if not isinstance(raw, bytes) or len(raw) % 2 or not 96000 <= len(raw) <= 640000:
        raise ValueError('Require bounded 3–20s PCM16 audio')
    vad = webrtcvad.Vad(2)
    frame_bytes = 960  # 30ms at 16kHz PCM16
    frames = [raw[i:i+frame_bytes] for i in range(0,len(raw)-frame_bytes+1,frame_bytes)]
    speech = [i for i,frame in enumerate(frames) if vad.is_speech(frame,16000)]
    seconds = len(speech)*.03
    if seconds < minimum_seconds:
        raise ValueError('Insufficient VAD speech; use a longer single-speaker recording')
    first, last = max(0,speech[0]-5), min(len(frames),speech[-1]+6)
    return b''.join(frames[first:last]), {'vad_speech_seconds': round(seconds,3),
                                        'vad': 'webrtcvad-mode2-30ms'}


class EcapaEncoder:
    dimension = 192

    def __init__(self, model_directory, model_id=None):
        directory = Path(model_directory).resolve()
        if not directory.is_dir() or not (directory/'hyperparams.yaml').is_file():
            raise ValueError('Provision a complete local ECAPA model directory first')
        actual_id = verify_model(directory)
        if model_id is not None and model_id != actual_id:
            raise ValueError('Requested speaker model ID does not match files')
        from speechbrain.inference.classifiers import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy
        self.model_id = actual_id
        self.model = EncoderClassifier.from_hparams(
            source=str(directory), savedir=str(directory),
            overrides={'pretrained_path': str(directory).replace('\\', '/')},
            local_strategy=LocalStrategy.COPY,
            run_opts={'device': 'cpu'})

    def encode(self, raw):
        if not isinstance(raw, bytes) or len(raw) % 2 or not 3200 <= len(raw) <= 640000:
            raise ValueError('Require bounded PCM16 bytes')
        import torch
        waveform = torch.tensor(struct.unpack('<%dh' % (len(raw)//2), raw), dtype=torch.float32).unsqueeze(0)/32768
        with torch.inference_mode():
            return normalize(self.model.encode_batch(waveform).reshape(-1).tolist(), self.dimension)


def enrollment_vector(vectors, dimension, consistency):
    if not math.isfinite(consistency) or not -1 <= consistency <= 1:
        raise ValueError('Invalid consistency threshold')
    vectors = [normalize(v, dimension) for v in vectors]
    if len(vectors) < 3:
        raise ValueError('At least three distinct recordings required')
    if any(sum(a*b for a,b in zip(v, w)) < consistency
           for i,v in enumerate(vectors) for w in vectors[i+1:]):
        raise ValueError('Enrollment recordings disagree; do not commit')
    return normalize([sum(v[i] for v in vectors)/len(vectors) for i in range(dimension)], dimension)
