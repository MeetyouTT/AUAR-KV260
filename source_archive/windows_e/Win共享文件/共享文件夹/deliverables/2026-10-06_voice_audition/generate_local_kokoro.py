"""Generate the same audition lines with the project's existing Kokoro backend."""
import hashlib
import importlib.metadata
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

HERE = Path(__file__).resolve().parent
AURA = HERE.parents[1] / 'aura'
sys.path.insert(0, str(AURA))
from board.runtime.audio import tts


def main():
    plan = json.loads((HERE / 'audition_plan.json').read_text(encoding='utf-8'))
    # The existing native FST reader needs ASCII paths. Keep the disposable
    # junction in the OS temporary directory, without changing project code.
    tts._ASCII_LINK_ROOT_CANDS = (str(Path(tempfile.gettempdir()) / 'aura_voice_audition_20261006'),)
    directory = tts.ascii_path(AURA / 'models' / 'tts' / plan['kokoro_model'])
    if not str(directory).isascii():
        raise RuntimeError('An ASCII model junction is needed by the native FST reader')
    backend = tts.SherpaTtsBackend.__new__(tts.SherpaTtsBackend)
    backend.config = tts.TtsConfig(engine='vits', tts_model=plan['kokoro_model'], sid=plan['kokoro_sid'], num_threads=2)
    backend.model_dir = directory
    backend._sherpa = sherpa_onnx
    started = time.perf_counter()
    engine = backend._build_tts()
    report = {'environment': 'PC CPU / SIMULATED; no board or live device playback',
              'model': plan['kokoro_model'], 'voice': plan['kokoro_voice'], 'sid': plan['kokoro_sid'],
              'sample_rate': engine.sample_rate, 'num_speakers': engine.num_speakers,
              'model_load_seconds': time.perf_counter() - started,
              'style_control': 'speed only; no claim of instruction-based emotion control',
              'runtime': {'python': sys.version, 'sherpa-onnx': importlib.metadata.version('sherpa-onnx')},
              'clips': []}
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=True)
    for scene in plan['scenes']:
        print('GENERATING Kokoro / ' + scene['label'], flush=True)
        started = time.perf_counter()
        generated = engine.generate(scene['text'], sid=plan['kokoro_sid'], speed=scene['kokoro_speed'])
        wall = time.perf_counter() - started
        samples = np.asarray(generated.samples, dtype=np.float32)
        if not len(samples) or not np.isfinite(samples).all():
            raise ValueError('Invalid generated waveform')
        file = raw / ('kokoro_' + scene['id'] + '.wav')
        sf.write(file, samples, generated.sample_rate, subtype='PCM_16')
        row = {'voice': 'Kokoro', 'scene': scene['id'], 'text': scene['text'],
               'speed': scene['kokoro_speed'], 'file': file.name, 'sample_rate': generated.sample_rate,
               'duration_seconds': len(samples) / generated.sample_rate,
               'generation_wall_seconds': wall, 'rtf': wall / (len(samples) / generated.sample_rate),
               'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
        report['clips'].append(row)
        (HERE / 'kokoro_generation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('SAVED ' + file.name + f' ({row["duration_seconds"]:.2f}s; RTF={row["rtf"]:.2f})', flush=True)


if __name__ == '__main__':
    main()
