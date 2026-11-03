"""Public synthetic file benchmark only; root must enforce an external timeout.

No microphone, network, subprocess, database, deployment, or downloaded code.
The exact eight fixtures are authored synthesis intent, not human transcript gold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
import time
import types

sys.dont_write_bytecode = True
HELPER_SHA = '293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
MANIFEST_SHA = '7109ee213126f098a3a3da08bbc521beb0db54a21e0911be02e04f2010b9a869'
ADAPTER_SHA = '4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
PINS = {
    'sensevoice': ('c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51',
                  'f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc'),
    'paraformer': ('f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945',
                   '59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'),
}
# Remove only documented SenseVoice metadata tags, only at output edges.
# Unknown tags or a tag occurring inside the spoken text remain observable.
KNOWN_TAGS = frozenset('<|' + x + '|>' for x in (
    'zh', 'en', 'yue', 'ja', 'ko', 'nospeech', 'auto',
    'NEUTRAL', 'HAPPY', 'SAD', 'ANGRY', 'FEARFUL', 'DISGUSTED', 'SURPRISED', 'EMO_UNKNOWN',
    'Speech', 'BGM', 'Applause', 'Laughter', 'Cry', 'Sneeze', 'Breath', 'Cough',
    'Sing', 'Speech_Noise', 'Event_UNK', 'withitn', 'woitn'))
ERROR_CODES = frozenset((
    'HELPER_PATH_INVALID', 'HELPER_PIN_MISMATCH', 'CANCELLED', 'SOFT_DEADLINE_EXCEEDED',
    'ARGUMENTS_INVALID', 'DEADLINE_REQUIRED', 'MANIFEST_PIN_UNAPPROVED', 'ADAPTER_ARGUMENT_INVALID',
    'MODEL_PATH_INVALID', 'ADAPTER_PATH_INVALID', 'SHERPA_VERSION_MISMATCH',
    'EXTRA_RECOGNIZER_CONSTRUCTION', 'PCM_INVALID', 'HYPOTHESIS_INVALID', 'NOT_LINUX_AARCH64',
    'PUBLIC_PATH_INVALID', 'PUBLIC_PATH_OUTSIDE_ROOT', 'PUBLIC_FILE_MISSING', 'HASH_INVALID',
    'PINNED_FILE_INVALID', 'PINNED_FILE_SIZE_INVALID', 'PIN_MISMATCH', 'MODEL_RESOURCE_INVALID',
    'MODEL_PIN_MISMATCH', 'TEXT_SIZE_INVALID', 'MANIFEST_PROVENANCE_INVALID', 'CASE_SET_INVALID',
    'CASE_TEXT_INVALID', 'WAV_DECLARATION_INVALID', 'WAV_PATH_REUSED', 'WAV_FORMAT_INVALID',
    'WAV_PCM_INVALID'))


class Refused(Exception):
    pass


def require(ok, code):
    if not ok:
        raise Refused(code)


def load_helper(path):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'HELPER_PATH_INVALID')
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == HELPER_SHA,
            'HELPER_PIN_MISMATCH')
    helper = types.ModuleType('_pinned_public_quality_helper')
    exec(compile(raw, '<pinned_public_quality_helper>', 'exec'), helper.__dict__)
    return helper


def strip_known_edge_tags(text):
    cleaned, removed = text.strip(), []
    while True:
        match = re.match(r'<\|[^<>|]{1,40}\|>', cleaned)
        if not match or match.group() not in KNOWN_TAGS:
            break
        removed.append(match.group())
        cleaned = cleaned[match.end():].lstrip()
    while True:
        match = re.search(r'<\|[^<>|]{1,40}\|>$', cleaned)
        if not match or match.group() not in KNOWN_TAGS:
            break
        removed.append(match.group())
        cleaned = cleaned[:match.start()].rstrip()
    return cleaned, removed


def check_budget(deadline, cancelled=lambda: False, clock=time.monotonic):
    require(not cancelled(), 'CANCELLED')
    require(clock() < deadline, 'SOFT_DEADLINE_EXCEEDED')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('ARGUMENTS_INVALID')


def parse_args(argv=None):
    p = Parser(description=__doc__)
    p.add_argument('--engine', required=True, choices=('sensevoice', 'paraformer'))
    p.add_argument('--manifest', required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--helper', default=str(Path(__file__).with_name('public_quality_helper.py')))
    p.add_argument('--model-dir', required=True)
    p.add_argument('--paraformer-source')
    p.add_argument('--threads', type=int, default=3, choices=(1, 2, 3))
    p.add_argument('--rounds', type=int, default=1, choices=(1, 2))
    p.add_argument('--max-seconds', type=int, default=120)
    p.add_argument('--external-deadline-managed', required=True, action='store_true')
    args = p.parse_args(argv)
    require(args.external_deadline_managed and 30 <= args.max_seconds <= 300,
            'DEADLINE_REQUIRED')
    require(args.manifest_sha256 == MANIFEST_SHA, 'MANIFEST_PIN_UNAPPROVED')
    require((args.engine == 'paraformer') == bool(args.paraformer_source),
            'ADAPTER_ARGUMENT_INVALID')
    return args


def prepare(args, helper, *, wall=time.perf_counter, cpu=time.process_time):
    start, start_cpu = wall(), cpu()
    raw = helper.pinned_bytes(helper.public_path(args.manifest), MANIFEST_SHA, 65536)
    audio = helper.validate_manifest(json.loads(raw))
    directory = Path(args.model_dir)
    require(directory.is_absolute() and directory.is_dir()
            and '..' not in directory.parts
            and not any(p.is_symlink() for p in (directory, *directory.parents))
            and 'win共享文件' not in str(directory.resolve()).casefold(), 'MODEL_PATH_INVALID')
    model_sha, tokens_sha = PINS[args.engine]
    hash_start, hash_cpu = wall(), cpu()
    helper.verify_model_resource(directory / 'model.int8.onnx', model_sha, 300 * 1024 * 1024)
    helper.verify_model_resource(directory / 'tokens.txt', tokens_sha, 1024 * 1024)
    model_hash_wall_ms = round((wall()-hash_start)*1000, 3)
    model_hash_cpu_ms = round((cpu()-hash_cpu)*1000, 3)
    adapter = None
    if args.engine == 'paraformer':
        path = Path(args.paraformer_source)
        require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
                'ADAPTER_PATH_INVALID')
        source = helper.pinned_bytes(path, ADAPTER_SHA, 32768)
        module = types.ModuleType('_pinned_paraformer_adapter')
        exec(compile(source, '<pinned_paraformer_adapter>', 'exec'), module.__dict__)
        adapter = module.BoardParaformer
    return dict(audio=audio, directory=directory, adapter=adapter,
                model_hash_wall_ms=model_hash_wall_ms, model_hash_cpu_ms=model_hash_cpu_ms,
                validation_wall_ms=round((wall()-start)*1000, 3),
                validation_cpu_ms=round((cpu()-start_cpu)*1000, 3))


def construct(args, prepared, sherpa, *, wall=time.perf_counter, cpu=time.process_time):
    require(sherpa.__version__ == '1.13.8', 'SHERPA_VERSION_MISMATCH')
    directory = prepared['directory']
    model_sha, tokens_sha = PINS[args.engine]
    stats = {'recognizer_constructions': 0}
    original_factory = (sherpa.OfflineRecognizer.from_sense_voice if args.engine == 'sensevoice'
                        else sherpa.OfflineRecognizer.from_paraformer)

    def measured_factory(**kwargs):
        require(stats['recognizer_constructions'] == 0, 'EXTRA_RECOGNIZER_CONSTRUCTION')
        stats['recognizer_constructions'] += 1
        start, start_cpu = wall(), cpu()
        result = original_factory(**kwargs)
        stats['load_wall_ms'] = round((wall()-start)*1000, 3)
        stats['load_cpu_ms'] = round((cpu()-start_cpu)*1000, 3)
        return result

    start, start_cpu = wall(), cpu()
    if args.engine == 'sensevoice':
        recognizer = measured_factory(model=str(directory / 'model.int8.onnx'),
            tokens=str(directory / 'tokens.txt'), num_threads=args.threads,
            sample_rate=16000, feature_dim=80, language='zh', use_itn=False,
            decoding_method='greedy_search', provider='cpu', debug=False)
    else:
        recognizer = prepared['adapter'](str(directory), model_sha256=model_sha,
            tokens_sha256=tokens_sha, num_threads=args.threads, recognizer_factory=measured_factory)
    stats['constructor_total_wall_ms'] = round((wall()-start)*1000, 3)
    stats['constructor_total_cpu_ms'] = round((cpu()-start_cpu)*1000, 3)
    stats['constructor_nonfactory_wall_ms'] = round(
        stats['constructor_total_wall_ms']-stats['load_wall_ms'], 3)
    stats['constructor_nonfactory_cpu_ms'] = round(
        stats['constructor_total_cpu_ms']-stats['load_cpu_ms'], 3)
    stats['constructor_nonfactory_scope'] = ('baseline adapter repeats pinned resource verification and initializes adapter'
        if args.engine == 'paraformer' else 'Python argument construction')
    return recognizer, stats


def decode_case(engine, recognizer, np, pcm, deadline, *, cancelled=lambda: False,
                clock=time.monotonic, wall=time.perf_counter, cpu=time.process_time):
    require(isinstance(pcm, bytes) and 0 < len(pcm) <= 640000 and len(pcm) % 2 == 0,
            'PCM_INVALID')
    check_budget(deadline, cancelled, clock)
    start, start_cpu = wall(), cpu()
    if engine == 'paraformer':
        raw = recognizer.transcribe(pcm, sample_rate=16000, deadline=deadline, cancelled=cancelled)
    else:
        samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        recognizer.decode_stream(stream)
        raw = stream.result.text
    elapsed, elapsed_cpu = (wall()-start)*1000, (cpu()-start_cpu)*1000
    check_budget(deadline, cancelled, clock)
    require(isinstance(raw, str) and len(raw) <= 1000, 'HYPOTHESIS_INVALID')
    text, tags = strip_known_edge_tags(raw) if engine == 'sensevoice' else (raw, [])
    return raw, text, tags, round(elapsed, 3), round(elapsed_cpu, 3)


def evaluate(args, prepared, helper, recognizer, np, deadline, *, cancelled=lambda: False,
             clock=time.monotonic, wall=time.perf_counter, cpu=time.process_time):
    rows = []
    for repeat in range(1, args.rounds+1):
        for case, spans, pcm in prepared['audio']:
            raw, text, tags, elapsed, elapsed_cpu = decode_case(args.engine, recognizer, np, pcm, deadline,
                cancelled=cancelled, clock=clock, wall=wall, cpu=cpu)
            rows.append(dict(id=case['id'], ordinal=len(rows)+1, round_index=repeat,
                first_model_decode=not rows, repeated_input_round=repeat > 1,
                reference=case['reference_text'], hypothesis=text, raw_hypothesis=raw,
                removed_structured_edge_tags=tags, unknown_structured_tags_present=bool(re.search(r'<\|[^<>|]+\|>', text)),
                wav_sha256=case['sha256'], samples=case['samples'], rate=16000,
                audio_duration_ms=case['samples']/16, offline_decode_wall_ms=elapsed,
                offline_decode_cpu_ms=elapsed_cpu,
                intended_text_character_error=helper.character_error(case['reference_text'], text),
                critical_spans_literal_match=[dict(span=span, present=span in text) for span in spans],
                critical_spans_scope='literal_match_only',
                semantic_acceptance_passed=None))
    return rows


def main(argv=None):
    args = parse_args(argv)
    require(platform.system() == 'Linux' and platform.machine() == 'aarch64', 'NOT_LINUX_AARCH64')
    deadline = time.monotonic()+args.max_seconds
    helper = load_helper(args.helper)
    prepared = prepare(args, helper)
    check_budget(deadline)
    with helper.quiet_native():
        start, start_cpu = time.perf_counter(), time.process_time()
        import numpy as np
        import sherpa_onnx
        imports = dict(runtime_import_wall_ms=round((time.perf_counter()-start)*1000, 3),
                       runtime_import_cpu_ms=round((time.process_time()-start_cpu)*1000, 3))
        check_budget(deadline)
        recognizer, stats = construct(args, prepared, sherpa_onnx)
        check_budget(deadline)
        rows = evaluate(args, prepared, helper, recognizer, np, deadline)
    import resource
    edits = sum(row['intended_text_character_error']['edit_distance'] for row in rows)
    chars = sum(row['intended_text_character_error']['reference_chars'] for row in rows)
    return dict(schema_version=1, status='PUBLIC_ASR_MEASURED_NOT_ACCEPTED', engine=args.engine,
        mode='offline_public_files_not_endpoint_or_end_to_end_latency', asr_threads=args.threads,
        rounds=args.rounds, hidden_warmup_runs=0, sherpa_version='1.13.8',
        language='zh' if args.engine == 'sensevoice' else None, use_itn=False,
        manifest_sha256=MANIFEST_SHA, helper_sha256=HELPER_SHA,
        adapter_sha256=ADAPTER_SHA if args.engine == 'paraformer' else None,
        model_sha256=PINS[args.engine][0], tokens_sha256=PINS[args.engine][1],
        public_synthetic=True, intended_not_human_verified=True, gold_human_reference=False,
        semantic_acceptance_passed=None, production_written=False, microphone_opened=False,
        external_deadline_required=True, soft_deadline_seconds=args.max_seconds,
        validation_wall_ms=prepared['validation_wall_ms'], validation_cpu_ms=prepared['validation_cpu_ms'],
        model_hash_wall_ms=prepared['model_hash_wall_ms'], model_hash_cpu_ms=prepared['model_hash_cpu_ms'],
        validation_scope='manifest/audio/model pins and optional baseline adapter source; before model loading',
        **imports, **stats, aggregate_edit_distance=edits, aggregate_reference_chars=chars,
        aggregate_intended_text_cer=round(edits/chars, 6),
        decode_wall_sum_ms=round(sum(row['offline_decode_wall_ms'] for row in rows), 3),
        decode_cpu_sum_ms=round(sum(row['offline_decode_cpu_ms'] for row in rows), 3),
        process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        peak_rss_scope='whole isolated process including runtime, pins, and model; Linux KiB', results=rows)


if __name__ == '__main__':
    try:
        print(json.dumps(main(), ensure_ascii=False, allow_nan=False))
    except KeyboardInterrupt:
        print('{"status":"INTERRUPTED","code":"CANCELLED"}')
        sys.exit(130)
    except Exception as error:
        code = str(error) if isinstance(error, Refused) or type(error).__name__ == 'Refused' else 'PUBLIC_ASR_WORKER_FAILED'
        if code not in ERROR_CODES:
            code = 'PUBLIC_ASR_WORKER_FAILED'
        print(json.dumps(dict(status='REFUSED_OR_FAILED', code=code)))
        sys.exit(2)
