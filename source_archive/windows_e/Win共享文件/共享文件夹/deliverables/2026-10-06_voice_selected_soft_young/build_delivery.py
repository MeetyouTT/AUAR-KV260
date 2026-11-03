"""Prepare a portable, level-aligned four-scene selected-voice audition."""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
RATE = 24000


def active_rms(samples):
    block = 480
    count = len(samples) // block
    if not count:
        return float(np.sqrt(np.mean(samples ** 2)))
    frames = samples[:count * block].reshape(count, block)
    values = np.sqrt(np.mean(frames ** 2, axis=1))
    keep = values > max(.0001, float(values.max()) * .1)
    return float(np.sqrt(np.mean(frames[keep] ** 2))) if keep.any() else 0.0


def main():
    selection = json.loads((HERE / 'selection.json').read_text(encoding='utf-8'))
    scenes = json.loads((HERE / 'scenes.json').read_text(encoding='utf-8'))['scenes']
    generation = json.loads((HERE / 'generation.json').read_text(encoding='utf-8'))
    if generation['status'] != 'COMPLETE':
        raise ValueError('Generation is not complete')
    output = HERE / 'audio'
    output.mkdir(exist_ok=True)
    assets = HERE / 'assets'
    assets.mkdir(exist_ok=True)
    shutil.copy2(HERE.parents[1] / 'aura/assets/avatar/idle_normal/000000.png', assets / 'avatar.png')
    clips = []
    checks = []
    combined = []
    cursor = 0.0
    report_by_id = {row['id']: row for row in generation['clips']}
    for scene in scenes:
        source = HERE / 'raw' / (scene['id'] + '.wav')
        samples, rate = sf.read(source, dtype='float32', always_2d=True)
        if rate != RATE or samples.shape[1] != 1 or not np.isfinite(samples).all():
            raise ValueError('Invalid source audio: ' + source.name)
        samples = samples[:, 0]
        duration = len(samples) / rate
        peak = float(np.max(np.abs(samples)))
        rms = active_rms(samples)
        if not .5 < duration < 90 or peak < .001 or rms < .0001:
            raise ValueError('Invalid source signal: ' + source.name)
        gain = min(.1 / rms, .95 / peak)
        normalized = samples * gain
        target = output / source.name
        sf.write(target, normalized, RATE, subtype='PCM_16')
        if combined:
            combined.append(np.zeros(int(RATE * .65), dtype=np.float32))
            cursor += .65
        start = cursor
        combined.append(normalized)
        cursor += duration
        clips.append({'id': scene['id'], 'label': scene['label'], 'text': scene['text'],
                      'file': 'audio/' + target.name, 'duration_seconds': duration,
                      'start_seconds': start, 'end_seconds': cursor})
        checks.append({'id': scene['id'], 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                       'recorded_source_sha256': report_by_id[scene['id']]['sha256'],
                       'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                       'sample_rate': rate, 'channels': 1, 'duration_seconds': duration,
                       'gain': gain, 'normalized_peak': float(np.max(np.abs(normalized))),
                       'normalized_active_rms': active_rms(normalized),
                       'clipped_samples': int(np.sum(np.abs(normalized) >= 1))})
    all_file = output / 'soft_young_all.wav'
    sf.write(all_file, np.concatenate(combined), RATE, subtype='PCM_16')
    comparison = {'title': '小光 · 柔亮俏皮固定声线', 'status': 'SELECTED',
                  'selected_name': selection['selected_name'],
                  'file': 'audio/' + all_file.name, 'clips': clips}
    (HERE / 'comparison.json').write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    passed = all(row['source_sha256'] == row['recorded_source_sha256'] and row['clipped_samples'] == 0 for row in checks)
    verification = {'status': 'PASS' if passed else 'FAIL', 'validated_clips': len(checks),
                    'sample_rate': RATE,
                    'normalization': '20ms gated active-RMS target 0.1, peak ceiling 0.95; approximate, not LUFS',
                    'limits': 'File/signal checks do not verify pronunciation, emotion, or identity by listening.',
                    'clips': checks}
    (HERE / 'audio_verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': verification['status'], 'clips': len(checks)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
