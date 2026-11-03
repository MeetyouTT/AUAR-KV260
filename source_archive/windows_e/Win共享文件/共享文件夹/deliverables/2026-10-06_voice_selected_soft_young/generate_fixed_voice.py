"""Freeze the selected VoiceDesign sample with one Base ICL prompt and generate four scenes."""
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
    selection = json.loads((HERE / 'selection.json').read_text(encoding='utf-8'))
    scenes = json.loads((HERE / 'scenes.json').read_text(encoding='utf-8'))['scenes']
    reference = (HERE / selection['reference_audio']).resolve(strict=True)
    if hashlib.sha256(reference.read_bytes()).hexdigest() != selection['reference_sha256']:
        raise ValueError('Selected reference audio hash changed')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = True
    started = time.perf_counter()
    print('LOADING selected voice Base model', flush=True)
    model = Qwen3TTSModel.from_pretrained(str(model_path), device_map='cuda:0',
                                         dtype=torch.bfloat16, attn_implementation='sdpa',
                                         local_files_only=True)
    print('BUILDING one reusable ICL voice prompt', flush=True)
    prompt_started = time.perf_counter()
    prompt = model.create_voice_clone_prompt(ref_audio=str(reference),
                    ref_text=selection['reference_text'], x_vector_only_mode=False)
    report = {
        'status': 'IN_PROGRESS', 'selected_name': selection['selected_name'],
        'environment': 'PC CUDA / SIMULATED; not board inference',
        'model': 'Qwen/Qwen3-TTS-12Hz-1.7B-Base',
        'model_revision': json.loads((HERE / 'base_model_verification.json').read_text(encoding='utf-8'))['revision'],
        'model_path': str(model_path), 'attention': 'sdpa', 'dtype': 'bfloat16',
        'gpu': torch.cuda.get_device_name(0), 'python': sys.version,
        'packages': {name: metadata.version(name) for name in ['qwen-tts','torch','torchaudio','transformers','numpy','soundfile']},
        'reference_audio': selection['reference_audio'], 'reference_text': selection['reference_text'],
        'reference_sha256': selection['reference_sha256'], 'x_vector_only_mode': False,
        'model_load_seconds': time.perf_counter() - started,
        'prompt_build_seconds': time.perf_counter() - prompt_started,
        'clips': []
    }
    raw = HERE / 'raw'
    raw.mkdir(exist_ok=True)
    for index, scene in enumerate(scenes):
        target = raw / (scene['id'] + '.wav')
        if target.exists():
            raise FileExistsError('Preserve prior generated file: ' + target.name)
        torch.manual_seed(8600 + index)
        torch.cuda.reset_peak_memory_stats()
        print('GENERATING ' + scene['label'], flush=True)
        clip_started = time.perf_counter()
        with torch.inference_mode():
            waves, rate = model.generate_voice_clone(text=scene['text'], language='Chinese',
                voice_clone_prompt=prompt, non_streaming_mode=True, max_new_tokens=600)
        elapsed = time.perf_counter() - clip_started
        samples = np.asarray(waves[0], dtype=np.float32)
        if samples.ndim != 1 or not len(samples) or not np.isfinite(samples).all():
            raise ValueError('Invalid generated waveform')
        sf.write(target, samples, rate, subtype='PCM_16')
        duration = len(samples) / rate
        report['clips'].append({'id': scene['id'], 'label': scene['label'], 'text': scene['text'],
            'file': target.name, 'seed': 8600 + index, 'sample_rate': int(rate),
            'duration_seconds': duration, 'generation_seconds': elapsed, 'rtf': elapsed / duration,
            'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        (HERE / 'generation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'SAVED {target.name} ({duration:.2f}s)', flush=True)
    report['status'] = 'COMPLETE'
    (HERE / 'generation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', required=True, type=Path)
    args = parser.parse_args()
    main(args.model_path.resolve(strict=True))
