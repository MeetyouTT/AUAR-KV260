"""Generate short VoiceDesign candidates, retaining a same-text Vivian reference."""
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


def generate(kind, model_path):
    plan = json.loads((HERE / 'audition_plan.json').read_text(encoding='utf-8'))
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    torch.set_num_threads(4)
    print('LOADING ' + kind, flush=True)
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(str(model_path), device_map='cuda:0',
                                        dtype=torch.bfloat16, attn_implementation='sdpa',
                                        local_files_only=True)
    report_file = HERE / ('reference_generation.json' if kind == 'reference' else 'design_generation.json')
    verification_file = HERE / 'model_verification.json'
    report = {'kind': kind, 'environment': 'PC CUDA / SIMULATED; not board inference',
              'model_path': str(model_path), 'gpu': torch.cuda.get_device_name(0), 'python': sys.version,
              'model_load_seconds': time.perf_counter() - started,
              'model_revision': json.loads(verification_file.read_text(encoding='utf-8'))['revision'] if kind == 'design' else '0c0e3051f131929182e2c023b9537f8b1c68adfe',
              'model': 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign' if kind == 'design' else 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
              'attention': 'sdpa', 'dtype': 'bfloat16', 'clips': []}
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=True)
    rows = [plan['reference']] if kind == 'reference' else plan['candidates']
    for item in rows:
        destination = raw / (item['id'] + '.wav')
        if destination.exists():
            raise FileExistsError('Preserve previous samples; use a new audition version')
        torch.manual_seed(item['seed'])
        torch.cuda.reset_peak_memory_stats()
        print('GENERATING ' + item['name'], flush=True)
        started = time.perf_counter()
        with torch.inference_mode():
            if kind == 'reference':
                waves, rate = model.generate_custom_voice(text=plan['text'], language='Chinese', speaker='Vivian',
                            instruct=item['instruction'], non_streaming_mode=True, max_new_tokens=600)
            else:
                waves, rate = model.generate_voice_design(text=plan['text'], language='Chinese',
                            instruct=item['instruction'], non_streaming_mode=True, max_new_tokens=600)
        elapsed = time.perf_counter() - started
        wave = np.asarray(waves[0], dtype=np.float32)
        if wave.ndim != 1 or not len(wave) or not np.isfinite(wave).all():
            raise ValueError('Invalid generated waveform')
        sf.write(destination, wave, rate, subtype='PCM_16')
        seconds = len(wave) / rate
        report['clips'].append({'id': item['id'], 'name': item['name'], 'file': destination.name,
             'text': plan['text'], 'instruction': item['instruction'], 'seed': item['seed'],
             'sample_rate': int(rate), 'duration_seconds': seconds, 'generation_seconds': elapsed,
             'rtf': elapsed / seconds, 'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
             'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'SAVED {destination.name} ({seconds:.2f}s)', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['reference', 'design'], required=True)
    parser.add_argument('--model-path', required=True, type=Path)
    args = parser.parse_args()
    generate(args.kind, args.model_path.resolve(strict=True))
