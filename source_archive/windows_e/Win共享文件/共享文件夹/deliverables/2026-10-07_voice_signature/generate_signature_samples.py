"""Generate the A/B/C signature candidates on the same line; the current formula stays as control.

Run on the machine that holds Qwen3-TTS VoiceDesign (PC CUDA / SIMULATED; not board inference).
Prior samples are preserved: an existing raw/<id>.wav aborts instead of being overwritten.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

HERE = Path(__file__).resolve().parent


def main(model_path, revision):
    plan = json.loads((HERE / 'signature_plan.json').read_text(encoding='utf-8'))
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    torch.set_num_threads(4)
    print('LOADING VoiceDesign model', flush=True)
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(str(model_path), device_map='cuda:0',
                                          dtype=torch.bfloat16, attn_implementation='sdpa',
                                          local_files_only=True)
    report = {'kind': 'design', 'environment': 'PC CUDA / SIMULATED; not board inference',
              'model_path': str(model_path), 'gpu': torch.cuda.get_device_name(0), 'python': sys.version,
              'model_load_seconds': time.perf_counter() - started, 'model_revision': revision,
              'model_revision_expected': plan.get('model_revision_expected'),
              'model': plan['voice_model'], 'attention': 'sdpa', 'dtype': 'bfloat16',
              'text': plan['text'], 'clips': []}
    if revision and plan.get('model_revision_expected') and revision != plan['model_revision_expected']:
        report['revision_mismatch'] = True
        print('WARNING: model revision differs from the plan record', flush=True)
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=True)
    report_file = HERE / 'signature_generation.json'
    for item in plan['candidates']:
        destination = raw / (item['id'] + '.wav')
        if destination.exists():
            raise FileExistsError('Preserve previous samples; use a new audition version')
        torch.manual_seed(item['seed'])
        torch.cuda.reset_peak_memory_stats()
        print('GENERATING ' + item['name'], flush=True)
        clip_started = time.perf_counter()
        with torch.inference_mode():
            waves, rate = model.generate_voice_design(text=plan['text'], language='Chinese',
                        instruct=item['instruction'], non_streaming_mode=True, max_new_tokens=600)
        elapsed = time.perf_counter() - clip_started
        wave = np.asarray(waves[0], dtype=np.float32)
        if wave.ndim != 1 or not len(wave) or not np.isfinite(wave).all():
            raise ValueError('Invalid generated waveform')
        sf.write(destination, wave, rate, subtype='PCM_16')
        seconds = len(wave) / rate
        report['clips'].append({'id': item['id'], 'role': item['role'], 'name': item['name'],
             'description': item['description'], 'file': destination.name, 'text': plan['text'],
             'instruction': item['instruction'], 'seed': item['seed'], 'sample_rate': int(rate),
             'duration_seconds': seconds, 'generation_seconds': elapsed, 'rtf': elapsed / seconds,
             'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
             'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'SAVED {destination.name} ({seconds:.2f}s)', flush=True)
    print('DONE: ' + str(len(report['clips'])) + ' samples', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', required=True, type=Path)
    parser.add_argument('--model-revision', default='')
    arguments = parser.parse_args()
    main(arguments.model_path.resolve(strict=True), arguments.model_revision)
