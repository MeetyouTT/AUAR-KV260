"""Level the four same-text samples to a common active RMS without changing pitch or speed.

The current formula is kept as the control row so the extra character in A/B/C stays comparable.
"""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent


def active_rms(samples):
    frames = samples[:len(samples) // 480 * 480].reshape(-1, 480)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    keep = rms > max(.0001, float(rms.max()) * .1)
    return float(np.sqrt(np.mean(frames[keep] ** 2))) if keep.any() else 0


def main():
    plan = json.loads((HERE / 'signature_plan.json').read_text(encoding='utf-8'))
    audio = HERE / 'audio'
    audio.mkdir(exist_ok=True)
    assets = HERE / 'assets'
    assets.mkdir(exist_ok=True)
    avatar_source = HERE.parents[1] / 'aura/assets/avatar/idle_normal/000000.png'
    if avatar_source.is_file():
        shutil.copy2(avatar_source, assets / 'avatar.png')
    rows = []
    checks = []
    for item in plan['candidates']:
        source = HERE / 'raw' / (item['id'] + '.wav')
        samples, rate = sf.read(source, dtype='float32', always_2d=True)
        if rate != 24000 or samples.shape[1] != 1 or not np.isfinite(samples).all():
            raise ValueError('Invalid audio format: ' + source.name)
        samples = samples[:, 0]
        peak = float(np.max(np.abs(samples)))
        rms = active_rms(samples)
        seconds = len(samples) / rate
        if peak < .001 or rms < .0001 or not 1 < seconds < 60:
            raise ValueError('Invalid audio signal: ' + source.name)
        gain = min(.1 / rms, .95 / peak)
        target = audio / source.name
        sf.write(target, samples * gain, rate, subtype='PCM_16')
        rows.append({'id': item['id'], 'role': item['role'], 'name': item['name'],
                     'description': item['description'], 'file': 'audio/' + target.name,
                     'duration_seconds': seconds, 'is_reference': item['role'] == 'baseline'})
        checks.append({'id': item['id'], 'sample_rate': rate, 'channels': 1, 'duration_seconds': seconds,
           'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
           'gain': gain, 'normalized_peak': peak * gain,
           'clipped_samples': int(np.sum(np.abs(samples * gain) >= 1))})
    (HERE / 'comparison.json').write_text(json.dumps({'title': plan['title'], 'text': plan['text'],
         'voices': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'audio_verification.json').write_text(json.dumps({'status': 'PASS', 'clips': checks,
         'normalization': '20ms gated active RMS target 0.1, peak ceiling 0.95; not LUFS',
         'limits': 'Checks cover file format and signal only; whether a sample is distinctive and still '
                   'sounds like the same young character requires human listening.'}, ensure_ascii=False, indent=2) + '\n',
         encoding='utf-8')
    print('PASS: ' + str(len(rows)) + ' same-text samples (1 control + candidates)', flush=True)


if __name__ == '__main__':
    main()
