"""Prepare portable WAV comparisons; retain unmodified generated originals."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
RATE = 24000


def active_rms(samples, rate):
    block = int(rate * .02)
    count = len(samples) // block
    if not count:
        return float(np.sqrt(np.mean(samples ** 2)))
    blocks = samples[:count * block].reshape(count, block)
    values = np.sqrt(np.mean(blocks ** 2, axis=1))
    mask = values > max(.0001, float(values.max()) * .1)
    return float(np.sqrt(np.mean(blocks[mask] ** 2))) if mask.any() else 0.0


def build():
    plan = json.loads((HERE / 'audition_plan.json').read_text(encoding='utf-8'))
    output = HERE / 'audio'
    output.mkdir(exist_ok=True)
    assets = HERE / 'assets'
    assets.mkdir(exist_ok=True)
    shutil.copy2(HERE.parents[1] / 'aura' / 'assets' / 'avatar' / 'idle_normal' / '000000.png', assets / 'avatar.png')
    comparisons = []
    checks = []
    missing = []
    descriptions = {'Serena': '温柔、亲近', 'Vivian': '清亮活泼的游戏少女方向', 'Kokoro': '现有中文女声'}
    for voice in plan['voices']:
        clips = []
        combined = []
        cursor = 0.0
        for scene in plan['scenes']:
            name = voice.lower() + '_' + scene['id'] + '.wav'
            source = HERE / 'raw_local' / name if voice != 'Kokoro' else HERE / 'raw' / name
            if voice != 'Kokoro' and not source.exists():
                source = HERE / 'raw' / name
            if not source.exists():
                missing.append({'voice': voice, 'scene': scene['id']})
                continue
            samples, rate = sf.read(source, dtype='float32', always_2d=True)
            if rate != RATE or samples.shape[1] != 1:
                raise ValueError('Unexpected source format: ' + source.name)
            samples = samples[:, 0]
            duration = len(samples) / rate
            peak = float(np.max(np.abs(samples)))
            rms = active_rms(samples, rate)
            if not .5 < duration < 90 or not np.isfinite(samples).all() or peak < .001 or rms < .0001:
                raise ValueError('Invalid source audio: ' + source.name)
            gain = min(.1 / rms, .95 / peak)
            normalized = samples * gain
            target = output / name
            sf.write(target, normalized, rate, subtype='PCM_16')
            cue = {'id': scene['id'], 'label': scene['label'], 'text': scene['text'],
                   'file': 'audio/' + name, 'duration_seconds': duration,
                   'source_backend': 'Kokoro local CPU' if voice == 'Kokoro' else ('Qwen local CUDA' if source.parent.name == 'raw_local' else 'Qwen official demo'),
                   'start_seconds': cursor, 'end_seconds': cursor + duration}
            clips.append(cue)
            if combined:
                combined.append(np.zeros(int(RATE * .65), dtype=np.float32))
            combined.append(normalized)
            cursor += duration + .65
            checks.append({'voice': voice, 'scene': scene['id'], 'source': source.relative_to(HERE).as_posix(),
                           'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                           'output': target.relative_to(HERE).as_posix(),
                           'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                           'sample_rate': rate, 'channels': 1, 'duration_seconds': duration,
                           'source_peak': peak, 'gain': gain,
                           'normalized_active_rms': active_rms(normalized, rate),
                           'normalized_peak': float(np.max(np.abs(normalized))),
                           'clipped_samples': int(np.sum(np.abs(normalized) >= 1))})
        complete = len(clips) == len(plan['scenes'])
        whole = None
        if clips:
            whole = 'audio/' + voice.lower() + '_all.wav'
            sf.write(HERE / whole, np.concatenate(combined), RATE, subtype='PCM_16')
        comparisons.append({'name': voice, 'description': descriptions[voice], 'complete': complete,
                            'file': whole, 'clips': clips,
                            'style_note': '本轮通过语气指令控制' if voice != 'Kokoro' else '本轮主要调整语速，情绪变化较有限'})
    result = {'title': plan['title'], 'complete': not missing, 'voices': comparisons,
              'user_preference': plan.get('user_preference', ''),
              'scenes': plan['scenes'], 'updated_utc': datetime.now(timezone.utc).isoformat()}
    (HERE / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    verification = {'status': 'PASS' if not missing else 'INCOMPLETE', 'missing': missing,
                    'validated_clips': len(checks), 'sample_rate': RATE,
                    'normalization': '20ms gated active-RMS target 0.1, peak ceiling 0.95; approximate listening level, not LUFS',
                    'limits': 'Signal/file checks do not verify pronunciation or perceived quality; listening required.',
                    'clips': checks}
    (HERE / 'audio_verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': verification['status'], 'clips': len(checks), 'missing': missing}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    build()
