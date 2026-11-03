"""Produce a matched local 1.7B audition, keeping the earlier remote samples."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

HERE = Path(__file__).resolve().parent


def main(model_path):
    plan = json.loads((HERE / 'audition_plan.json').read_text(encoding='utf-8'))
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA was not available; do not silently change the tested backend')
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = True
    started = time.perf_counter()
    print('LOADING local Qwen3-TTS 1.7B / CUDA / bfloat16 / SDPA', flush=True)
    model = Qwen3TTSModel.from_pretrained(str(model_path), device_map='cuda:0',
                                       dtype=torch.bfloat16, attn_implementation='sdpa',
                                       local_files_only=True)
    report_path = HERE / 'qwen_local_generation.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {
        'environment': 'PC CUDA / SIMULATED; not board inference',
        'model': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
        'model_revision': '0c0e3051f131929182e2c023b9537f8b1c68adfe',
        'model_path': str(model_path), 'attention': 'sdpa', 'dtype': 'bfloat16',
        'gpu': torch.cuda.get_device_name(0), 'python': sys.version,
        'packages': {name: metadata.version(name) for name in ['qwen-tts', 'torch', 'torchaudio', 'transformers', 'accelerate', 'numpy', 'soundfile']},
        'model_load_seconds': time.perf_counter() - started,
        'clips': [],
    }
    directory = HERE / 'raw_local'
    directory.mkdir(exist_ok=True)
    for voice in ['Vivian', 'Serena']:
        for index, scene in enumerate(plan['scenes']):
            target = directory / (voice.lower() + '_' + scene['id'] + '.wav')
            if target.exists() and any(row['file'] == target.name for row in report['clips']):
                print('EXISTING ' + target.name, flush=True)
                continue
            torch.manual_seed(4242 + index)
            torch.cuda.reset_peak_memory_stats()
            print('GENERATING local ' + voice + ' / ' + scene['label'], flush=True)
            started = time.perf_counter()
            instruction = plan.get('voice_instructions', {}).get(voice, {}).get(scene['id'], scene['instruction'])
            with torch.inference_mode():
                waves, rate = model.generate_custom_voice(
                    text=scene['text'], language='Chinese', speaker=voice,
                    instruct=instruction, non_streaming_mode=True,
                    max_new_tokens=600)
            wall = time.perf_counter() - started
            samples = np.asarray(waves[0], dtype=np.float32)
            if samples.ndim != 1 or not len(samples) or not np.isfinite(samples).all():
                raise ValueError('Invalid generated waveform')
            sf.write(target, samples, rate, subtype='PCM_16')
            row = {'voice': voice, 'scene': scene['id'], 'text': scene['text'],
                   'instruction': instruction, 'seed': 4242 + index,
                   'file': target.name, 'sample_rate': int(rate),
                   'duration_seconds': len(samples) / rate,
                   'generation_wall_seconds': wall, 'rtf': wall / (len(samples) / rate),
                   'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
                   'peak_cuda_reserved_bytes': torch.cuda.max_memory_reserved(),
                   'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
            report['clips'].append(row)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print('SAVED ' + target.name + f' ({row["duration_seconds"]:.2f}s; RTF={row["rtf"]:.2f})', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', required=True, type=Path)
    args = parser.parse_args()
    main(args.model_path.resolve(strict=True))
