"""Root-only public OfflineParaformer3 nice0/-5/-5/0 probe; default inspect.

No microphone, playback, private DB, production writes or affinity changes.
Only a fresh slot child owns the reviewed priority lease and ASR model.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
import wave

GUARD_SHA = '210925ca35fb5acdf90e96c08f9fe4713042637dd777d707c8ccb4134cdecf69'
PIPELINE_SHA = 'ac0af16c9f783b5590ab0e1562ece179b8cc50ade3912c8b08e8b8592778e093'
ASR_SHA = '4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
MODEL_SHA = 'f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945'
TOKEN_SHA = '59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'
WAV = '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav'
WAV_SHA = '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
ASR_DEPS = '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps'
ORDER = (0, -5, -5, 0)
ERRORS = frozenset(('helper_pin_changed', 'only_nice_zero_or_minus_five', 'asr_pin_changed',
    'public_wave_format_changed', 'public_wave_pin_changed', 'post_load_headroom',
    'priority_not_restored', 'production_owner_changed', 'owned_child_identity_changed',
    'parent_priority_changed', 'owned_child_group_changed', 'owned_child_failed',
    'owned_slot_metadata_invalid', 'owned_child_timeout', 'owned_group_remaining',
    'dependency_unavailable', 'probe_memory_error', 'probe_os_error', 'probe_invalid_metadata',
    'probe_runtime_error', 'unexpected_probe_error'))


class Refused(RuntimeError):
    def __init__(self, code): self.code = code


def failure_code(error, guard=None):
    allowed = ERRORS | getattr(guard, 'ERROR_CODES', frozenset())
    if getattr(error, 'code', None) in allowed: return error.code
    return {subprocess.TimeoutExpired:'owned_child_timeout', ImportError:'dependency_unavailable',
        MemoryError:'probe_memory_error', OSError:'probe_os_error', ValueError:'probe_invalid_metadata',
        RuntimeError:'probe_runtime_error'}.get(type(error), 'unexpected_probe_error')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path, expected):
    if sha(path) != expected: raise Refused('helper_pin_changed')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def priority_lease(pipeline, nice):
    if type(nice) is not int or nice not in (0, -5):
        raise Refused('only_nice_zero_or_minus_five')
    return pipeline.ProbeProcessPriority(nice)


def model_arguments(directory):
    return dict(model_dir=directory, model_sha256=MODEL_SHA, tokens_sha256=TOKEN_SHA, num_threads=3)


def idle_metadata(args, guard, *, clock=time.monotonic, sleep=time.sleep):
    # Only the existing scheduler-busy guard is transient; never weaken any gate.
    deadline = clock() + 20.
    last_busy = None
    while True:
        if last_busy is not None and clock() >= deadline: raise last_busy
        try:
            value = guard.metadata(args)
            if last_busy is not None and clock() > deadline: raise last_busy
            return value
        except Exception as error:
            if getattr(error, 'code', None) != 'model_or_background_summary_active': raise
            last_busy = error
            remaining = deadline - clock()
            if remaining <= 0: raise
            sleep(min(.25, remaining))


def numeric_context(guard, args):
    """Only fixed public numeric counters; absent fields remain unavailable."""
    def select(value, paths):
        result = {}
        for path in paths:
            item = value
            for key in path.split('.'):
                item = item.get(key) if isinstance(item, dict) else None
            if type(item) in (int, float) and math.isfinite(item): result[path] = item
        return result
    try:
        state = guard.get('127.0.0.1', 8783, '/api/state')
        value = dict(observed_mono=time.monotonic(), gui=select(state, (
            'avatar_display.frames', 'avatar_display.target_fps', 'avatar_display.paint_at')))
        value['gui_numeric_available'] = bool(value['gui'])
        if args.camera_health_port is not None:
            camera = guard.get('127.0.0.1', args.camera_health_port, '/health')
            value['camera'] = select(camera, ('capture_frames', 'detected_frames', 'preview_frames',
                'observation_frame_id', 'capture_age_ms', 'observation_age_ms', 'capture_hz',
                'detection_hz', 'preview_hz', 'last_inference_ms'))
        else: value['camera'] = {}
        value['camera_numeric_available'] = bool(value['camera'])
        return value
    except Exception:
        return dict(available=False, error_code='numeric_metadata_unavailable')


def slot(args, guard):
    idle_metadata(args, guard)  # Requires child nice0 before loading any model.
    pipeline = load('_priority_helper', args.pipeline_source, PIPELINE_SHA)
    code = Path(args.runtime_root)/'runtime/aura'
    sys.path[:0] = [str(code), ASR_DEPS]
    from board.runtime.audio.board_asr import BoardParaformer
    if sha(code/'board/runtime/audio/board_asr.py') != ASR_SHA: raise Refused('asr_pin_changed')
    with wave.open(WAV, 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
            raise Refused('public_wave_format_changed')
        pcm = wav.readframes(wav.getnframes())
    if sha(WAV) != WAV_SHA: raise Refused('public_wave_pin_changed')
    config = json.loads((code/'config/board_avatar_gtk.json').read_bytes())['board_business']
    began = time.monotonic()
    model = BoardParaformer(**model_arguments(config['asr_directory']))
    load_ms = (time.monotonic()-began)*1000
    if guard.available_mib() < args.min_available_mib: raise Refused('post_load_headroom')
    before = idle_metadata(args, guard)  # Loading is excluded from this comparison bracket.
    counters_before = numeric_context(guard, args)
    lease = priority_lease(pipeline, args.slot_nice)
    # Enumerates existing model/ORT threads, and restores newly created tasks too.
    with lease:
        warm_started = time.monotonic()
        warm = model.transcribe(pcm, deadline=warm_started+30.)
        warm_ms = (time.monotonic()-warm_started)*1000
        began, cpu = time.monotonic(), time.process_time()
        text = model.transcribe(pcm, deadline=began+30.)
        decode_ms, decode_cpu_ms = (time.monotonic()-began)*1000, (time.process_time()-cpu)*1000
    if lease.record.get('restoration_confirmed') is not True: raise Refused('priority_not_restored')
    counters_after = numeric_context(guard, args)
    after = guard.metadata(args, allow_background=True)  # Restored nice0 first.
    if before['ui'] != after['ui'] or before['camera'] != after['camera']:
        raise Refused('production_owner_changed')
    import resource
    return dict(status='PUBLIC_SLOT_MEASURED', nice=args.slot_nice, asr_threads=3,
        load_ms=load_ms, warmup_ms=warm_ms, decode_ms=decode_ms, decode_cpu_ms=decode_cpu_ms,
        audio_seconds=len(pcm)/32000, public_result_chars=len(text),
        public_result_sha256=hashlib.sha256(text.encode()).hexdigest(), same_as_warmup=text==warm,
        before=before, after=after, counters_before=counters_before, counters_after=counters_after,
        counters_scope='After load/headroom, around priority warmup+decode and adjacent metadata; not measured render FPS.',
        background_changed=before['memory'] != after['memory'] or not after['model_idle'],
        priority=dict(lease.record), peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        extra_asr_resident=True, production_asr_also_resident=True, actual_fps_acceptance=False,
        production_changed=False, microphone_opened=False, audio_played=False, private_store_accessed=False)


def kill_owned(process, birth, guard):
    if process.poll() is not None: return
    if (process.pid == os.getpid() or os.getpgid(process.pid) != process.pid
            or process.pid == os.getpgrp() or guard.proc(process.pid)['birth'] != birth):
        raise Refused('owned_child_identity_changed')
    os.killpg(process.pid, signal.SIGKILL)


def run_child(args, nice, guard):
    priority_lease(load('_parent_priority_helper', args.pipeline_source, PIPELINE_SHA), nice)
    if os.getpriority(os.PRIO_PROCESS, 0) != 0: raise Refused('parent_priority_changed')
    command = [sys.executable, '-B', str(Path(__file__).resolve())] + sys.argv[1:] + ['--slot-nice', str(nice)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True, env=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1'))
    birth = None
    try:
        birth = guard.proc(process.pid)['birth']
        if os.getpgid(process.pid) != process.pid: raise Refused('owned_child_group_changed')
        stdout, stderr = process.communicate(timeout=120)
        if len(stdout.encode()) > 65536: raise Refused('owned_child_failed')
        value = json.loads(stdout)
        if process.returncode != 0:
            code = value.get('error_code')
            raise Refused(code if code in ERRORS | guard.ERROR_CODES else 'owned_child_failed')
        if value.get('status') != 'PUBLIC_SLOT_MEASURED' or value.get('nice') != nice or value.get('asr_threads') != 3:
            raise Refused('owned_slot_metadata_invalid')
        value['owned_group_cleanup_verified'] = True
        return value
    finally:
        if process.poll() is None:
            if birth is None: birth = guard.proc(process.pid)['birth']
            kill_owned(process, birth, guard); process.communicate(timeout=5)
        # Do not signal a group after losing its leader's birth proof.
        try: os.killpg(process.pid, 0)
        except ProcessLookupError: pass
        else: raise Refused('owned_group_remaining')
        if os.getpriority(os.PRIO_PROCESS, 0) != 0: raise Refused('parent_priority_changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--slot-nice', type=int, choices=(0,-5), help=argparse.SUPPRESS)
    parser.add_argument('--guard-source', default='/home/root/aura-public-asr-thread-abba-20261031/210925ca35fb5acd/probe_asr_abba.py')
    parser.add_argument('--pipeline-source', required=True)
    parser.add_argument('--runtime-root', default='/home/root/aura-board-business-20261030/production-5259eab11e42af13')
    for name in ('startup-sha256','boot-id'): parser.add_argument('--'+name, required=True)
    for name in ('ui-pid','ui-birth','camera-pid','camera-birth'): parser.add_argument('--'+name, required=True, type=int)
    parser.add_argument('--camera-health-port', type=int)
    parser.add_argument('--min-available-mib', type=int, default=1500)
    args = parser.parse_args()
    if args.min_available_mib < 512 or args.camera_health_port is not None and not 1<=args.camera_health_port<=65535:
        parser.error('invalid fixed resource/metadata limits')
    if args.slot_nice is not None and not args.run: parser.error('slot requires explicit --run')
    results = []
    guard = None
    try:
        guard = load('_original_guard', args.guard_source, GUARD_SHA)
        if args.slot_nice is not None:
            value = slot(args, guard)
        else:
            before = idle_metadata(args, guard)
            if not args.run:
                value = dict(status='INSPECT_ONLY_NO_MODEL', before=before, order=list(ORDER), asr_threads=3)
            else:
                for nice in ORDER: results.append(run_child(args, nice, guard))
                after = guard.metadata(args, allow_background=True)
                a = statistics.median(r['decode_ms'] for r in results if r['nice']==0)
                b = statistics.median(r['decode_ms'] for r in results if r['nice']==-5)
                background = any(r['background_changed'] for r in results) or before['memory'] != after['memory'] or not after['model_idle']
                same = all(r['same_as_warmup'] for r in results) and len({r['public_result_sha256'] for r in results})==1
                value = dict(status='PUBLIC_FIXED_ASR_PRIORITY_ABBA_MEASURED', results=results,
                    before=before, after=after, order=list(ORDER), asr_threads=3, background_changed=background,
                    same_public_transcript=same, comparison_status='BACKGROUND_CHANGED_NO_GAIN_CLAIM' if background else 'DESCRIPTIVE_ONLY' if same else 'TRANSCRIPT_CHANGED_NO_GAIN_CLAIM',
                    nice0_median_ms=a, nice_minus5_median_ms=b, descriptive_reduction_percent=100*(1-b/a),
                    causal_gain_claimed=False, actual_fps_acceptance=False, production_changed=False,
                    microphone_opened=False, audio_played=False, private_store_accessed=False)
        print(json.dumps(value, allow_nan=False)); return 0
    except Exception as error:
        print(json.dumps(dict(status='PUBLIC_ASR_SCHEDULING_INCOMPLETE_NO_GAIN' if results else 'PUBLIC_ASR_SCHEDULING_REFUSED',
            error_code=failure_code(error, guard), completed_results=results, causal_gain_claimed=False)))
        return 1


if __name__ == '__main__': raise SystemExit(main())
