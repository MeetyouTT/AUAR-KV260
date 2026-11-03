"""One root-controlled public PCM slot for the existing combined frontend.

Default execution validates sources only. Model execution is ARM-only and uses
the existing resource pins and the prior reviewed raw-eight-frame probe.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time


ALLOCATION_SHA = 'c7988d2439fbb0d7d4c9d9b9783f3d1ce228cb61ccfd01d54a6ce05762ca9a3b'
PUMP_SHA = 'ac0af16c9f783b5590ab0e1562ece179b8cc50ade3912c8b08e8b8592778e093'
WAV_SHA = '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
SOURCE_PINS = {
    'board/runtime/audio/board_gtcrn_reuse.py': 'fd6e095d66e9a2b93e9fc738c93ccb8559daea02faa0f6d3d055d65c53de03a9',
    'board/runtime/audio/board_gtcrn_fft.py': '47cb8a2ec97ad292981bb42b67e217ed0f672a98d561d4ac8dc9c360cf8f6f06',
    'board/runtime/audio/board_asr_frontend.py': 'b3d06b653876469daf5b7bb805458b187662d9862e8ece6da731cbfa3e23a093',
    'board/runtime/audio/automatic_capture.py': '5e7abc5a15840aff51d0471313498a46efc940f16d4bd7ee95fed65f98fdcc0a',
    'board/runtime/audio/board_pcm_queue.py': 'b38c922d3c7446458bbd0ca4bf99316ec769fb52f3baf4525aa24923cccf300d',
    'board/runtime/audio/board_capture.py': '61859c4af6ccfdd3d583c07d681d4d5b4e8f1a1f076fa5059ede4f8c008117be',
}


def digest(path):
    path = Path(path)
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError('regular_file_required')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path, expected):
    if digest(path) != expected:
        raise ValueError('reviewed_probe_helper_changed')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_sources(args):
    mapping = json.loads(args.source_mapping.read_text(encoding='utf-8-sig'))
    root = Path(mapping['root'])
    if args.code_root != root/'runtime/aura':
        raise ValueError('production_code_root_mismatch')
    if digest(root/'startup/config.json') != mapping['startup_sha256']:
        raise ValueError('startup_changed')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != mapping['boot_id']:
        raise ValueError('board_boot_changed')
    for relative, expected in mapping['component_pins'].items():
        if digest(args.code_root/relative) != expected:
            raise ValueError('production_component_changed')
    for relative, expected in SOURCE_PINS.items():
        if mapping['component_pins'].get(relative) != expected:
            raise ValueError('reviewed_frontend_component_changed')
    return mapping


@contextmanager
def selected_session_policy(ort, model_path, mode):
    """Change one session constructor only inside this isolated test process."""
    if mode not in ('baseline_1', 'dual_nospin'):
        raise ValueError('unknown_frontend_session_policy')
    original = ort.InferenceSession
    threads = 1 if mode == 'baseline_1' else 2
    record = dict(mode=mode, intra_op_threads=threads, inter_op_threads=1,
                  intra_op_spinning='default' if threads == 1 else '0', sessions_created=0)

    def create(path, *, sess_options, providers):
        if (Path(path) != model_path or providers != ['CPUExecutionProvider']
                or sess_options.intra_op_num_threads != threads
                or sess_options.inter_op_num_threads != 1 or record['sessions_created']):
            raise ValueError('unexpected_frontend_session')
        if threads == 2:
            sess_options.add_session_config_entry('session.intra_op.allow_spinning', '0')
        session = original(path, sess_options=sess_options, providers=providers)
        actual = session.get_session_options()
        if (actual.intra_op_num_threads != threads or actual.inter_op_num_threads != 1
                or session.get_providers() != ['CPUExecutionProvider']):
            raise ValueError('frontend_session_policy_not_applied')
        if threads == 2 and actual.get_session_config_entry('session.intra_op.allow_spinning') != '0':
            raise ValueError('frontend_spinning_policy_not_applied')
        record['sessions_created'] += 1
        return session

    ort.InferenceSession = create
    try:
        yield record
        if record['sessions_created'] != 1:
            raise ValueError('exactly_one_gtcrn_session_required')
    finally:
        ort.InferenceSession = original


class TimedDenoiser:
    def __init__(self, inner, np):
        self.inner, self.np = inner, np
        self.clear()

    def clear(self):
        self.wall_ms = []
        self.thread_cpu_ms = []
        self.float_digest = hashlib.sha256()
        self.pcm_digest = hashlib.sha256()
        self.samples = self.hops = 0
        self.stages = dict(fft_ms=0., ort_ms=0., ifft_ola_ms=0.)

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def __call__(self, values, rate):
        began, cpu = time.monotonic(), time.thread_time()
        result = self.inner(values, rate)
        self.wall_ms.append((time.monotonic()-began)*1000)
        self.thread_cpu_ms.append((time.thread_time()-cpu)*1000)
        self.samples += len(result.samples)
        self.float_digest.update(result.samples.astype('<f4', copy=False).tobytes())
        pcm = self.np.rint(result.samples*32768).clip(-32768,32767).astype('<i2').tobytes()
        self.pcm_digest.update(pcm)
        self.hops += self.inner.last_timing['hops']
        for key in self.stages:
            self.stages[key] += self.inner.last_timing[key]
        return result


class TimedVad:
    def __init__(self, inner):
        self.inner = inner
        self.clear()

    def clear(self):
        self.wall_ms = self.thread_cpu_ms = 0.
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def accept_waveform(self, values):
        began, cpu = time.monotonic(), time.thread_time()
        try:
            return self.inner.accept_waveform(values)
        finally:
            self.wall_ms += (time.monotonic()-began)*1000
            self.thread_cpu_ms += (time.thread_time()-cpu)*1000
            self.calls += 1


def throughput(gate, board, np, framed, parent, deadline):
    # Original pool reset/lease semantics are reused between both repetitions.
    original_denoiser, original_vad = gate.denoiser, gate.vad
    denoiser, vad = TimedDenoiser(original_denoiser,np), TimedVad(original_vad)
    gate.denoiser, gate.vad = denoiser, vad
    pool = board.BoardFrontendPool(gate)
    rows = []
    try:
        for repetition in range(2):
            denoiser.clear()
            vad.clear()
            lease = pool.acquire()
            wall, cpu, process_cpu, decisions = [], [], [], []
            try:
                for offset in range(0,len(framed),640):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('public_frontend_deadline')
                    values = np.frombuffer(framed[offset:offset+640],dtype='<i2').astype(np.float32)/32768
                    began, thread_began, process_began = time.monotonic(), time.thread_time(), time.process_time()
                    decisions.append(bool(lease(values)))
                    wall.append((time.monotonic()-began)*1000)
                    cpu.append((time.thread_time()-thread_began)*1000)
                    process_cpu.append((time.process_time()-process_began)*1000)
            finally:
                lease.close()
            rows.append(dict(repetition=repetition+1, frames=len(decisions), input_seconds=len(framed)/32000,
                gate_wall_ms=parent.statistics_ms(wall), gate_consumer_cpu_ms=parent.statistics_ms(cpu),
                gate_process_cpu_ms=parent.statistics_ms(process_cpu),
                frame_windows=parent.timing_windows(wall),
                gtcrn_wall_ms=parent.statistics_ms(denoiser.wall_ms),
                gtcrn_consumer_cpu_ms=parent.statistics_ms(denoiser.thread_cpu_ms),
                gtcrn_stage_wall_total_ms=dict(denoiser.stages),
                vad_accept_wall_total_ms=vad.wall_ms, vad_accept_consumer_cpu_total_ms=vad.thread_cpu_ms,
                vad_accept_calls=vad.calls, model_hops=denoiser.hops, output_samples=denoiser.samples,
                output_float32_sha256=denoiser.float_digest.hexdigest(),
                output_pcm16_sha256=denoiser.pcm_digest.hexdigest(),
                decision_sha256=hashlib.sha256(bytes(decisions)).hexdigest(),
                decision_bytes_hex=bytes(decisions).hex(), process_cpu_includes_ort_workers=True))
    finally:
        pool.close()
        gate.denoiser, gate.vad = original_denoiser, original_vad
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-only', action='store_true')
    parser.add_argument('--mode', choices=('baseline_1','dual_nospin'), required=True)
    parser.add_argument('--slot', choices=('A1','B1','B2','A2'), required=True)
    parser.add_argument('--source-mapping', type=Path, required=True)
    parser.add_argument('--code-root', type=Path, required=True)
    parser.add_argument('--pipeline-helper', type=Path, required=True)
    parser.add_argument('--pump-helper', type=Path, required=True)
    parser.add_argument('--wav', type=Path, required=True)
    parser.add_argument('--frontend-models', type=Path, required=True)
    parser.add_argument('--fft-deps', type=Path, required=True)
    parser.add_argument('--asr-deps', type=Path, required=True)
    args = parser.parse_args()
    if args.slot.startswith('A') != (args.mode == 'baseline_1'):
        parser.error('A slots are baseline_1 and B slots are dual_nospin')
    if os.name != 'posix' or platform.machine().lower() not in ('aarch64','arm64'):
        parser.error('This execution entry is ARM Linux only')
    mapping = validate_sources(args)
    allocation = load('_reviewed_public_allocation_helpers', args.pipeline_helper, ALLOCATION_SHA)
    parent = load('_reviewed_public_pcm_helpers', args.pump_helper, PUMP_SHA)
    pcm, framed = allocation.public_pcm(args.wav)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_READY', source_components_verified=len(mapping['component_pins']),
                             mode=args.mode, slot=args.slot, public_wav_sha256=WAV_SHA)))
        return 0
    before = parent.safety_snapshot()
    if before['boot_id'] != mapping['boot_id']:
        raise ValueError('board_boot_changed_before_model_load')
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        if os.environ.get(key) != '1':
            raise ValueError('explicit_single_thread_math_environment_required')
    priority = parent.ProbeProcessPriority(-10)
    started = time.monotonic()
    deadline = started+75.
    result = dict(status='FAILED', error_code='public_probe_incomplete')
    gate = None
    try:
        with priority:
            np, runtime = allocation.runtime(args)
            ort = sys.modules['onnxruntime']
            sys.path.insert(0,str(args.code_root))
            modules = {name:importlib.import_module(name) for name in
                       ('board.runtime.audio.board_capture','board.runtime.audio.automatic_capture',
                        'board.runtime.audio.board_gtcrn_reuse')}
            for relative, expected in SOURCE_PINS.items():
                module = importlib.import_module(relative[:-3].replace('/','.'))
                if Path(module.__file__).resolve() != args.code_root/relative or digest(Path(module.__file__)) != expected:
                    raise ValueError('executed_frontend_source_mismatch')
            reuse = modules['board.runtime.audio.board_gtcrn_reuse']
            load_start, load_cpu = time.monotonic(), time.process_time()
            with selected_session_policy(ort,args.frontend_models/'gtcrn_simple.onnx',args.mode) as policy:
                gate = reuse.ReuseFftSpeechGate(args.frontend_models,
                    num_threads=policy['intra_op_threads'], buffer_reuse=True, io_binding=True, profile=True)
            load_metrics = dict(wall_ms=(time.monotonic()-load_start)*1000,
                                process_cpu_ms=(time.process_time()-load_cpu)*1000)
            direct = throughput(gate,modules['board.runtime.audio.board_capture'],np,framed,parent,deadline)
            paced = allocation.pipeline(parent,modules,gate,np,pcm,framed,deadline)
            result = dict(status='PASS_PUBLIC_SLOT' if paced['status']=='PASS_PUBLIC_PUMP_ENDPOINT_ONLY' else 'FAILED',
                error_code=paced['error_code'], session_policy=policy, load=load_metrics,
                throughput=direct, paced=paced, runtime=runtime, gate_instances=1,
                constructor_zero_warmup_frames=32, profile=True,
                model_sha256=dict(importlib.import_module('board.runtime.audio.board_asr_frontend').HASHES))
    except Exception as error:
        result.update(status='FAILED', error_code='public_probe_failed', error_class=type(error).__name__
                      if type(error).__name__ in ('ValueError','RuntimeError','TimeoutError','OSError','MemoryError') else 'other')
    finally:
        if gate is not None:
            gate.close()
    after = parent.safety_snapshot()
    if before != after or not priority.record.get('restoration_confirmed'):
        result.update(status='FAILED', error_code='owner_state_or_priority_not_restored')
    validate_sources(args)
    result.update(schema='aura.public-frontend-budget-slot.v1', slot=args.slot, mode=args.mode,
        startup_sha256=mapping['startup_sha256'], source_components_verified=len(mapping['component_pins']),
        source_wav_sha256=WAV_SHA, total_wall_seconds=time.monotonic()-started,
        before=before, after=after, priority=dict(priority.record),
        original_pcm_and_endpoint_used=True, queue_capacity_frames=8,
        soft_deadline_seconds=75, external_hard_timeout_required=True,
        asr_executed=False, microphone_opened=False, audio_played=False,
        production_source_modified=False, production_database_opened=False,
        measured_scope='Public existing-gate throughput and paced raw8 endpoint. Physical dialogue acceptance remains separate.')
    print(json.dumps(result),flush=True)
    return 0 if result['status']=='PASS_PUBLIC_SLOT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
