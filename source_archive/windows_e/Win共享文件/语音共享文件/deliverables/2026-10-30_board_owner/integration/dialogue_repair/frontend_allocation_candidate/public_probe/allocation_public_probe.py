"""One isolated public-WAV allocation slot; root supplies the external timeout.

No ASR, microphone, player, network, database, download or production write.
Only this process's nice is changed/restored by the reviewed parent helper.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
import wave

ROOT = Path(__file__).resolve().parents[1]
PINS_SHA = '01627e6abefa8b655a66c2617c1cb4bb3f6c7ee80cd051050304618e59792369'
WAV_SHA = '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
WAV_SAMPLES = 89834
VERSIONS = ('1.21.2', '1.17.3', '1.13.8')
MODULE_ORDER = ('host.model_service.protocol', 'common.frontend_wire',
    'board.runtime.audio.capture', 'board.runtime.audio.vad',
    'board.runtime.audio.automatic_capture', 'board.runtime.audio.echo_cancel',
    'tools.barge_in_capture', 'board.runtime.audio.board_pcm_queue',
    'board.runtime.audio.board_capture', 'board.runtime.audio.board_asr_frontend',
    'board.runtime.audio.board_gtcrn_fft', 'board.runtime.audio.board_gtcrn_reuse')


class Refused(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def regular(path, maximum=1024 * 1024):
    path = Path(path)
    if (not path.is_absolute() or path.is_symlink() or path.resolve(strict=True) != path
            or not path.is_file() or path.stat().st_size > maximum):
        raise Refused('regular_file_required')
    return path


def digest(path, maximum=1024 * 1024):
    return hashlib.sha256(regular(path, maximum).read_bytes()).hexdigest()


def validate_sources(arm, production_code, root=ROOT):
    pins_path = root / 'public_probe/PROBE_SOURCE_PINS.json'
    if digest(pins_path) != PINS_SHA:
        raise Refused('probe_manifest_pin')
    pins = json.loads(pins_path.read_text('utf-8'))
    if digest(root / 'HANDOFF.json') != pins['frozen_candidate_handoff_sha256']:
        raise Refused('frozen_candidate_changed')
    selected, proof = {}, {}
    for component, record in pins['components'].items():
        for item in ([record['before'], record['after']] if 'before' in record else [record]):
            if digest(root / item['relative_path']) != item['sha256']:
                raise Refused('isolated_source_pin')
        if digest(Path(production_code) / component) != record['production_sha256']:
            raise Refused('production_source_drift')
        item = record[arm] if 'before' in record else record
        selected[component.replace('/', '.')[:-3]] = root / item['relative_path']
        proof[component] = dict(sha256=item['sha256'],
            production_sha256=record['production_sha256'], relative_path=item['relative_path'])
    parent = root / pins['parent_probe']['relative_path']
    if digest(parent) != pins['parent_probe']['sha256']:
        raise Refused('reviewed_parent_probe_pin')
    return selected, proof, parent


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if '.' in name:
        owner, attribute = name.rsplit('.', 1)
        setattr(sys.modules[owner], attribute, module)
    return module


def load_isolated(selected):
    # Bind the selected canonical automatic module BEFORE board_capture imports
    # its class aliases. Never mutate an already-imported production MRO.
    packages = ('board', 'board.runtime', 'board.runtime.audio', 'host',
                'host.model_service', 'tools', 'common')
    if any(name in sys.modules for name in packages + MODULE_ORDER):
        raise Refused('fresh_source_process_required')
    for name in packages:
        value = ModuleType(name); value.__path__ = []
        sys.modules[name] = value
        if '.' in name:
            owner, attribute = name.rsplit('.', 1)
            setattr(sys.modules[owner], attribute, value)
    modules = {name: load_file(name, selected[name]) for name in MODULE_ORDER}
    automatic = modules['board.runtime.audio.automatic_capture']
    capture = modules['board.runtime.audio.board_capture']
    if (automatic.AutomaticMcp01Capture not in capture.BoardAutomaticCapture.__mro__
            or capture.SpeechEndpoint is not automatic.SpeechEndpoint):
        raise Refused('selected_endpoint_not_bound')
    for name, module in modules.items():
        if Path(module.__file__).resolve() != selected[name]:
            raise Refused('module_origin_drift')
    return modules


def public_pcm(path):
    if digest(path) != WAV_SHA:
        raise Refused('public_wav_pin')
    with wave.open(str(path), 'rb') as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(),
                stream.getnframes(), stream.getcomptype()) != (1, 2, 16000, WAV_SAMPLES, 'NONE'):
            raise Refused('public_wav_format')
        pcm = stream.readframes(WAV_SAMPLES)
    if len(pcm) != WAV_SAMPLES * 2:
        raise Refused('public_wav_truncated')
    # Same reviewed padding: complete final 640-byte frame, then 70 silent frames.
    return pcm, pcm + bytes((-len(pcm)) % 640) + bytes(640 * 70)


def runtime(args):
    if any(name in sys.modules for name in ('numpy', 'onnxruntime', 'sherpa_onnx')):
        raise Refused('fresh_native_process_required')
    roots = [Path(args.fft_deps), Path(args.asr_deps)]
    if any(not p.is_absolute() or p.resolve(strict=True) != p or not p.is_dir() for p in roots):
        raise Refused('runtime_root')
    sys.path[:0] = [str(p) for p in roots]
    np, ort, sherpa = [importlib.import_module(n) for n in ('numpy', 'onnxruntime', 'sherpa_onnx')]
    if (np.__version__, ort.__version__, sherpa.__version__) != VERSIONS:
        raise Refused('production_runtime_versions')
    if (roots[0] not in Path(ort.__file__).resolve().parents
            or roots[1] not in Path(sherpa.__file__).resolve().parents):
        raise Refused('runtime_origin')
    return np, dict(versions=dict(zip(('numpy', 'onnxruntime', 'sherpa_onnx'), VERSIONS)),
        origins={n: str(Path(m.__file__).resolve()) for n, m in
                 (('numpy', np), ('onnxruntime', ort), ('sherpa_onnx', sherpa))},
        provenance='Explicit existing dependency paths and versions; no alternate runtime selected')


class DenoisedObserver:
    def __init__(self, inner, np):
        self.inner, self.np = inner, np
        self.samples = self.calls = self.hops = 0
        self.float_digest, self.pcm_digest = hashlib.sha256(), hashlib.sha256()
        self.observer_cpu_seconds = 0.
        hop = inner._hop

        def counted(samples):
            self.hops += 1
            return hop(samples)
        inner._hop = counted

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def __call__(self, samples, sample_rate):
        result = self.inner(samples, sample_rate)
        began = time.thread_time()
        self.calls += 1
        self.samples += len(result.samples)
        self.float_digest.update(result.samples.astype('<f4', copy=False).tobytes())
        pcm = self.np.rint(result.samples * 32768).clip(-32768, 32767).astype('<i2').tobytes()
        self.pcm_digest.update(pcm)
        self.observer_cpu_seconds += time.thread_time() - began
        return result

    def public(self):
        return dict(calls=self.calls, model_hops=self.hops, samples=self.samples,
            float32_sha256=self.float_digest.hexdigest(), pcm16_sha256=self.pcm_digest.hexdigest(),
            pcm16_observation_only=True, observer_cpu_seconds=self.observer_cpu_seconds,
            timing_includes_equal_observer_overhead=True, flush_called=False)


def pipeline(parent, modules, gate, np, pcm, framed, deadline):
    source = parent.PacedPublicPcm(framed)
    board = modules['board.runtime.audio.board_capture']
    automatic = modules['board.runtime.audio.automatic_capture']
    denoised = DenoisedObserver(gate.denoiser, np)
    gate.denoiser = denoised
    pool = board.BoardFrontendPool(gate)
    capture = None
    durations, cpu_durations, decisions, onset = [], [], [], []
    began, cpu = time.monotonic(), time.process_time()
    result = dict(status='FAILED', error_code='public_pipeline_incomplete')

    class ObservedLease:
        def __init__(self):
            self.lease = pool.acquire()
        def __call__(self, frame):
            if threading.current_thread().name == 'aura-board-raw-pcm':
                raise Refused('model_on_producer')
            if time.monotonic() >= deadline:
                raise Refused('soft_deadline')
            start, thread_cpu = time.monotonic(), time.thread_time()
            try:
                value = self.lease(frame)
                decisions.append(bool(value))
                return value
            finally:
                durations.append((time.monotonic() - start) * 1000)
                cpu_durations.append((time.thread_time() - thread_cpu) * 1000)
        def close(self): self.lease.close()
        def public(self): return self.lease.public()

    def no_device(*args, **kwargs):
        raise Refused('device_process_forbidden')

    try:
        capture = board.BoardAutomaticCapture(lambda: False, max_seconds=20,
            frontend_factory=ObservedLease, process_factory=no_device)
        if capture.frontend_queue_frames != 8:
            raise Refused('raw_queue_not_eight')
        capture.endpoint = capture._endpoint()
        if type(capture.endpoint) is not automatic.SpeechEndpoint:
            raise Refused('wrong_endpoint_instance')
        capture.on_speech_start = lambda: onset.append(capture.endpoint.total_samples)
        capture._signal = lambda *_: source.stop()  # only this finite source, no PID signal
        captured = capture._read_pcm(SimpleNamespace(stdout=source))
        queue = capture._board_pcm_input.public()
        offset = capture.endpoint.start_sample * 2
        if (not captured or len(captured) % 2 or len(captured) > 20 * 32000
                or captured != framed[offset:offset + len(captured)]
                or queue['capacity_frames'] != 8 or queue['error'] or queue['reader_alive']
                or not capture.endpoint.done or len(onset) != 1
                or denoised.calls != len(decisions)
                or denoised.hops != len(decisions) * 320 // 256
                or denoised.samples != max(0, denoised.hops - 1) * 256):
            raise Refused('incomplete_or_noncontiguous_capture')
        result = dict(status='PASS_PUBLIC_PUMP_ENDPOINT_ONLY', error_code='NONE',
            endpoint=dict(onset_observed_total_samples=onset, end_total_samples=capture.endpoint.total_samples,
                start_sample=capture.endpoint.start_sample, captured_samples=len(captured)//2,
                original_pcm_sha256=hashlib.sha256(captured).hexdigest(),
                original_contiguous_pcm_preserved=True,
                decision_sha256=hashlib.sha256(bytes(decisions)).hexdigest()))
    except Exception as exc:
        allowed = {'pcm_input_queue_overflow', 'pcm_input_truncated_frame', 'pcm_input_read_failed',
            'pcm_input_reader_not_stopped', 'pcm_input_source_stop_failed', 'soft_deadline',
            'model_on_producer', 'raw_queue_not_eight', 'wrong_endpoint_instance',
            'incomplete_or_noncontiguous_capture', 'device_process_forbidden'}
        code = getattr(exc, 'code', 'public_pipeline_failed')
        result = dict(status='FAILED', error_code=code if code in allowed else 'public_pipeline_failed')
    finally:
        source.stop()
        pump = getattr(capture, '_board_pcm_input', None)
        if pump is not None and not pump.close():
            result = dict(status='FAILED', error_code='pcm_input_reader_not_stopped')
        if capture is not None:
            capture._close_endpoint()
            if capture._timer is not None: capture._timer.cancel()
        pool.close()
    result.update(wall_seconds=time.monotonic()-began, process_cpu_seconds=time.process_time()-cpu,
        frontend_wall_ms=parent.statistics_ms(durations), frontend_thread_cpu_ms=parent.statistics_ms(cpu_durations),
        frontend_windows=parent.timing_windows(durations), input_queue=pump.public() if pump else None,
        source_supply_lateness_ms=parent.statistics_ms(source.lateness_ms), source_produced_frames=source.frames,
        producer_thread=source.reader_thread, consumed_frames=len(decisions), denoised=denoised.public(),
        endpoint_diagnostics=dict(capture._endpoint_diagnostics) if capture else {},
        source_input_samples=len(pcm)//2, framed_samples=len(framed)//2,
        tail_padding_frames=70, source_frame_padding_samples=((-len(pcm))%640)//2,
        wall_scope='Capture construction/endpoint lease reset, paced consumption and owned cleanup; gate load separate',
        acceptance_scope='One public paced file, actual raw8 pump/endpoint; no physical capture or dialogue acceptance')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=('before', 'after'), required=True)
    parser.add_argument('--slot-id', choices=('A1', 'B1', 'B2', 'A2'), required=True)
    parser.add_argument('--production-code-root', type=Path, required=True)
    parser.add_argument('--wav', type=Path, required=True)
    parser.add_argument('--frontend-models', type=Path, required=True)
    parser.add_argument('--fft-deps', type=Path, required=True)
    parser.add_argument('--asr-deps', type=Path, required=True)
    parser.add_argument('--soft-seconds', type=int, choices=range(10, 61), default=60)
    args = parser.parse_args(argv)
    if (args.slot_id.startswith('A')) != (args.arm == 'before'):
        parser.error('A slots use before; B slots use after')
    value = dict(status='FAILED', error_code='probe_not_started')
    priority = None
    began = time.monotonic()
    deadline = began + args.soft_seconds
    try:
        if os.name != 'posix' or platform.machine().lower() not in ('aarch64', 'arm64'):
            raise Refused('native_arm_only')
        def expired(*_): raise Refused('soft_deadline')
        signal.signal(signal.SIGALRM, expired); signal.alarm(args.soft_seconds)
        selected, proof, parent_path = validate_sources(args.arm, args.production_code_root)
        parent = load_file('_reviewed_allocation_probe_helpers', parent_path)
        pcm, framed = public_pcm(args.wav)
        priority = parent.ProbeProcessPriority(-10)
        with priority:
            np, runtime_proof = runtime(args)
            modules = load_isolated(selected)
            reuse = modules['board.runtime.audio.board_gtcrn_reuse']
            load_at, load_cpu = time.monotonic(), time.process_time()
            # Exactly one combined gate, same weights/1-thread settings/32-frame warmup.
            gate = reuse.ReuseFftSpeechGate(args.frontend_models, num_threads=1,
                                           buffer_reuse=True, io_binding=True)
            load_seconds, load_cpu_seconds = time.monotonic()-load_at, time.process_time()-load_cpu
            value = pipeline(parent, modules, gate, np, pcm, framed, deadline)
            value.update(runtime=runtime_proof, selected_source_proof=proof,
                actual_endpoint_source_sha256=digest(selected['board.runtime.audio.automatic_capture']),
                actual_reuse_source_sha256=digest(selected['board.runtime.audio.board_gtcrn_reuse']),
                actual_automatic_mro=[cls.__module__+'.'+cls.__name__ for cls in
                    modules['board.runtime.audio.board_capture'].BoardAutomaticCapture.__mro__],
                gate_instances=1, gate_load_seconds=load_seconds, gate_load_cpu_seconds=load_cpu_seconds,
                model_sha256=dict(modules['board.runtime.audio.board_asr_frontend'].HASHES),
                constructor_zero_warmup_frames=32, profile=False, num_threads=1,
                buffer_reuse=True, io_binding=True)
    except Exception as exc:
        allowed = {'native_arm_only', 'soft_deadline', 'regular_file_required',
            'probe_manifest_pin', 'frozen_candidate_changed', 'isolated_source_pin',
            'production_source_drift', 'reviewed_parent_probe_pin', 'fresh_source_process_required',
            'selected_endpoint_not_bound', 'module_origin_drift', 'public_wav_pin',
            'public_wav_format', 'public_wav_truncated', 'fresh_native_process_required',
            'runtime_root', 'production_runtime_versions', 'runtime_origin',
            'probe_thread_membership_rejected', 'probe_main_thread_unavailable',
            'process_nice_not_supported', 'process_nice_effective_mismatch',
            'process_nice_permission_denied', 'process_nice_restore_failed'}
        code = getattr(exc, 'code', 'probe_failed')
        value.update(status='FAILED', error_code=code if code in allowed else 'probe_failed')
    finally:
        if os.name == 'posix': signal.alarm(0)
    value.update(arm=args.arm, slot_id=args.slot_id, source_wav_sha256=WAV_SHA,
        total_wall_seconds=time.monotonic()-began, soft_deadline_seconds=args.soft_seconds,
        external_hard_timeout_required=True, process_priority=dict(priority.record) if priority else None,
        asr_executed=False, microphone_opened=False, audio_played=False, production_database_opened=False,
        production_source_modified=False, systemwide_tuning=False, model_downloads=0)
    if priority is not None and not priority.record.get('restoration_confirmed'):
        value.update(status='FAILED', error_code='process_nice_restore_failed')
    print(json.dumps(value, sort_keys=True), flush=True)
    return 0 if value['status'] == 'PASS_PUBLIC_PUMP_ENDPOINT_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
