"""Isolated audition. No production imports, cache writes, or defaults changed."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import random
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VOICE = ROOT / 'deliverables/2026-10-06_voice_selected_soft_young'


def dump(path, value):
    tmp = path.with_suffix('.part.json')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def main(args):
    import numpy as np
    import soundfile as sf
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    selection = json.loads((VOICE / 'selection.json').read_text(encoding='utf-8'))
    reference = VOICE / selection['reference_audio']
    if hashlib.sha256(reference.read_bytes()).hexdigest() != selection['reference_sha256']:
        raise ValueError('Reference SHA256 changed')
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))['cases']
    if args.only:
        cases = [c for c in cases if c['id'] in args.only.split(',')]
        if not cases:
            raise ValueError('No matching cases')
    tag = args.engine + (f'_{args.steps}' if args.engine == 'omnivoice' else '')
    out = HERE / 'runs' / tag
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / 'report.json'
    old = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
    if old and old['reference_sha256'] != selection['reference_sha256']:
        raise ValueError('Existing report uses a different reference')
    torch.set_num_threads(4)
    started = time.perf_counter()
    print('LOADING ' + tag, flush=True)
    if args.engine == 'omnivoice':
        from omnivoice import OmniVoice
        model = OmniVoice.from_pretrained(str(args.model), device_map='cuda:0', dtype=torch.float16,
                                         attn_implementation='sdpa')
        prompt = model.create_voice_clone_prompt(ref_audio=str(reference), ref_text=selection['reference_text'])
        model_id = 'k2-fsa/OmniVoice'
        generation = dict(num_step=args.steps, speed=1.0, guidance_scale=2.0, denoise=True,
                          preprocess_prompt=True, postprocess_output=True)
    else:
        from qwen_tts import Qwen3TTSModel
        model = Qwen3TTSModel.from_pretrained(str(args.model), device_map='cuda:0', dtype=torch.bfloat16,
                                            attn_implementation='sdpa', local_files_only=True)
        prompt = model.create_voice_clone_prompt(ref_audio=str(reference), ref_text=selection['reference_text'],
                                                x_vector_only_mode=False)
        model_id = 'Qwen/Qwen3-TTS-12Hz-1.7B-Base'
        generation = dict(non_streaming_mode=True, max_new_tokens=1200)
    torch.cuda.synchronize()
    report = old or dict(engine=args.engine, model=model_id, model_revision=args.revision,
        reference_sha256=selection['reference_sha256'], reference_text=selection['reference_text'],
        seed=8701, parameters=generation, gpu=torch.cuda.get_device_name(0),
        attention='sdpa', dtype='float16' if args.engine=='omnivoice' else 'bfloat16',
        packages={p:metadata.version(p) for p in ['torch','torchaudio','transformers','numpy','soundfile',
                                                'omnivoice' if args.engine=='omnivoice' else 'qwen-tts']}, clips=[])
    if report['model_revision'] != args.revision or report['parameters'] != generation:
        raise ValueError('Existing report identity differs')
    report.update(status='IN_PROGRESS', load_and_prompt_seconds=time.perf_counter()-started,
                  timing_scope='synchronized complete synthesis, not first audible playback or board performance')
    sessions=report.setdefault('sessions',[])
    session_index=len(sessions)
    sessions.append(dict(load_and_prompt_seconds=report['load_and_prompt_seconds'],generated_ids=[]))
    generated_this_run=0
    dump(report_path, report)
    for case in cases:
        if any(c['id'] == case['id'] for c in report['clips']):
            continue
        raw_path = out / (case['id'] + '_raw.wav')
        if raw_path.exists():
            raise FileExistsError(raw_path)
        random.seed(8701); np.random.seed(8701); torch.manual_seed(8701)
        torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize()
        tick = time.perf_counter()
        print('GENERATING ' + case['id'], flush=True)
        with torch.inference_mode():
            if args.engine == 'omnivoice':
                samples = model.generate(text=case['text'], voice_clone_prompt=prompt, **generation)[0]
                rate = int(model.sampling_rate)
            else:
                waves, rate = model.generate_voice_clone(text=case['text'], language='Chinese',
                                                        voice_clone_prompt=prompt, **generation)
                samples = waves[0]
        torch.cuda.synchronize()
        elapsed = time.perf_counter()-tick
        samples = np.asarray(samples, dtype=np.float32)
        if rate != 24000 or samples.ndim != 1 or not samples.size or not np.isfinite(samples).all():
            raise ValueError('Invalid waveform')
        peak = float(np.abs(samples).max())
        rms = np.array([np.sqrt(np.mean(samples[i:i+480]**2)) for i in range(0,len(samples),480)])
        active = rms[rms > max(.005,float(rms.max())*.03)]
        if not active.size:
            raise ValueError('Silent waveform')
        gain = min(.1/float(np.sqrt(np.mean(active**2))), .95/max(peak,1e-6))
        # FLOAT preserves unmodified output; PCM16 is the level-matched audition.
        sf.write(raw_path, samples, rate, subtype='FLOAT')
        path = out / (case['id'] + '.wav')
        sf.write(path, samples*gain, rate, subtype='PCM_16')
        duration = len(samples)/rate
        report['clips'].append(dict(case, file=path.relative_to(HERE).as_posix(),
            raw_file=raw_path.relative_to(HERE).as_posix(), duration_seconds=duration,
            generation_seconds=elapsed, rtf=elapsed/duration, normalization_gain=gain,
            raw_peak=peak, raw_clipping_fraction=float(np.mean(np.abs(samples)>=1)),
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            session_index=session_index, first_after_load=generated_this_run==0))
        sessions[-1]['generated_ids'].append(case['id'])
        generated_this_run+=1
        dump(report_path,report)
        print(f'SAVED {case["id"]}: {duration:.2f}s, generation {elapsed:.3f}s', flush=True)
    report['status'] = 'COMPLETE' if len(report['clips'])==8 else 'PARTIAL'
    dump(report_path,report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=['omnivoice','qwen'], required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--steps', type=int, choices=[16,32], default=16)
    parser.add_argument('--only')
    main(parser.parse_args())
