"""Public-only paced combined frontend + independent one-thread OnlineCTC.

No production source/config/DB or microphone/player operation. Root executes.
Raw capture remains8 frames. Separate fixed1s ASR credit fails, never blocks tap.
"""
import argparse
from collections import deque
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import wave

HEADER = struct.Struct('!BII')
DATA, END, ACK, RESULT, READY, FAILED = range(1, 7)
ASR_PENDING_SAMPLES = 16000  #1s PCM16/32KiB; NOT the original8-frame capture queue.
MAX_BLOCK_SAMPLES = 320     #Exactly one original20ms RAW frame; GTCRN remains VAD-only.
CTC_MODEL_SHA = '68c9c943840f7d9cf3e8a4970ba50f404feb5277f611fa82b7e72267786fa84a'
CTC_TOKEN_SHA = '6fed8c6c248516f38e7faa19404b57413e8ce259f1cbc1fa4aebc86eac32fdfd'
GUARD_SHA = '210925ca35fb5acdf90e96c08f9fe4713042637dd777d707c8ccb4134cdecf69'


class Refused(RuntimeError):
    pass


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path, expected):
    if digest(path) != expected: raise Refused('source_pin_changed')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def send(stream, kind, sequence, payload=b''):
    if len(payload) > 16384: raise Refused('ipc_payload_limit')
    stream.sendall(HEADER.pack(kind, sequence, len(payload)) + payload)


def receive(stream):
    def exact(size):
        value = bytearray()
        while len(value) < size:
            raw = stream.recv(size-len(value))
            if not raw: raise Refused('ctc_peer_closed')
            value.extend(raw)
        return bytes(value)
    kind, sequence, size = HEADER.unpack(exact(HEADER.size))
    if kind not in (DATA, END, ACK, RESULT, READY, FAILED) or size > 16384:
        raise Refused('ipc_header_rejected')
    return kind, sequence, exact(size)


def attach_raw_tap(endpoint, sink):
    original_feed = endpoint.feed
    def feed_raw(raw):
        result = original_feed(raw)
        sink.offer(raw)
        return result
    endpoint.feed = feed_raw


class AsyncCtcSink:
    """Nonblocking tap; credits include queued, sent and unACKed samples.

    ACK comes after accept+drain, so socket buffers cannot hide extra backlog.
    Only the sender may block in sendall; native decoding lives in the child.
    """
    def __init__(self, stream, *, clock=time.monotonic):
        self.stream, self.clock = stream, clock
        self.lock = threading.Condition(); self.queue = deque(); self.pending = {}
        self.sequence = self.samples = self.outstanding = self.peak = 0
        self.oldest_max_ms = 0.; self.error = ''; self.closed = self.ended = False
        self.result = None; self.done = threading.Event(); self.sha = hashlib.sha256()
        self.sender = threading.Thread(target=self._send, daemon=True, name='public-ctc-sender')
        self.reader = threading.Thread(target=self._read, daemon=True, name='public-ctc-reader')
        self.sender.start(); self.reader.start()

    def offer(self, raw):
        if not isinstance(raw, bytes) or len(raw) != MAX_BLOCK_SAMPLES*2:
            raise Refused('raw_block_rejected')
        count = len(raw)//2
        with self.lock:
            if self.closed or self.ended or self.error: raise Refused('ctc_sink_unavailable')
            if self.outstanding + count > ASR_PENDING_SAMPLES:
                self.error = 'ctc_backlog_overflow'; self.lock.notify_all()
                raise Refused('ctc_backlog_overflow')
            self.sequence += 1; seq = self.sequence
            self.pending[seq] = (count, self.clock())
            self.outstanding += count; self.peak = max(self.peak, self.outstanding)
            self.samples += count; self.sha.update(raw)
            self.queue.append((DATA, seq, raw)); self.lock.notify_all()

    def finish(self, timeout=12.):
        with self.lock:
            if self.error or self.closed: raise Refused('ctc_sink_unavailable')
            self.ended = True
            body = json.dumps(dict(samples=self.samples, sha256=self.sha.hexdigest())).encode()
            self.queue.append((END, self.sequence+1, body)); self.lock.notify_all()
        if not self.done.wait(timeout): raise Refused('ctc_final_timeout')
        with self.lock:
            if self.error or self.result is None or self.outstanding:
                raise Refused('ctc_final_rejected')
            return dict(self.result)

    def _fail(self, code):
        with self.lock:
            if self.closed: return
            self.error = self.error or code; self.lock.notify_all(); self.done.set()

    def _send(self):
        try:
            while True:
                with self.lock:
                    self.lock.wait_for(lambda: self.queue or self.closed or self.error)
                    if self.closed or self.error: return
                    item = self.queue.popleft()
                send(self.stream, *item)
        except Exception: self._fail('ctc_send_failed')

    def _read(self):
        expected = 1
        try:
            while True:
                kind, sequence, raw = receive(self.stream)
                with self.lock:
                    if self.closed: return
                    if kind == ACK:
                        if sequence != expected or len(raw) != 4 or sequence not in self.pending:
                            raise Refused('ctc_ack_order')
                        count, began = self.pending.pop(sequence)
                        if struct.unpack('!I', raw)[0] != count: raise Refused('ctc_ack_count')
                        self.outstanding -= count; expected += 1
                        self.oldest_max_ms = max(self.oldest_max_ms, (self.clock()-began)*1000)
                    elif kind == RESULT and self.ended and sequence == self.sequence+1 and not self.pending:
                        self.result = json.loads(raw); self.done.set(); return
                    else: raise Refused('ctc_result_order')
        except Exception: self._fail('ctc_receive_failed')

    def public(self):
        with self.lock:
            return dict(capacity_samples=ASR_PENDING_SAMPLES, capacity_ms=1000,
                peak_samples=self.peak, peak_ms=self.peak/16, outstanding_samples=self.outstanding,
                oldest_ack_max_ms=round(self.oldest_max_ms, 3), sent_samples=self.samples,
                error=self.error, nonblocking_producer=True)

    def close(self):
        with self.lock:
            self.closed = True; self.queue.clear(); self.pending.clear(); self.lock.notify_all()
        try: self.stream.shutdown(socket.SHUT_RDWR)
        except OSError: pass
        self.stream.close()
        for thread in (self.sender, self.reader): thread.join(timeout=.5)
        return not self.sender.is_alive() and not self.reader.is_alive()


def ctc_worker(fd, model_root):
    stream = socket.socket(fileno=fd); stream.settimeout(30.)
    try:
        root = Path(model_root)
        if digest(root/'model.int8.onnx') != CTC_MODEL_SHA or digest(root/'tokens.txt') != CTC_TOKEN_SHA:
            raise Refused('ctc_model_pin_changed')
        import numpy as np
        import sherpa_onnx as sherpa
        if sherpa.__version__ != '1.13.8' or os.getpriority(os.PRIO_PROCESS, 0) != 0:
            raise Refused('ctc_runtime_or_priority_changed')
        started = time.monotonic()
        recognizer = sherpa.OnlineRecognizer.from_zipformer2_ctc(tokens=str(root/'tokens.txt'),
            model=str(root/'model.int8.onnx'), num_threads=1, sample_rate=16000, feature_dim=80,
            enable_endpoint_detection=False, decoding_method='greedy_search', provider='cpu', debug=False)
        audio = recognizer.create_stream(); calls = []; cpu_ms = 0.; samples = 0; sha = hashlib.sha256()
        send(stream, READY, 0, json.dumps(dict(load_ms=(time.monotonic()-started)*1000)).encode())
        first_input = None; expected = 1
        def drain():
            nonlocal cpu_ms
            while recognizer.is_ready(audio):
                if len(calls) >= 100: raise Refused('ctc_decode_budget')
                began, cpu = time.monotonic(), time.process_time()
                recognizer.decode_stream(audio)
                calls.append((time.monotonic()-began)*1000)
                cpu_ms += (time.process_time()-cpu)*1000
        while True:
            kind, sequence, raw = receive(stream)
            if sequence != expected: raise Refused('ctc_input_order')
            expected += 1
            if kind == DATA:
                if len(raw) != MAX_BLOCK_SAMPLES*2: raise Refused('ctc_input_size')
                values = np.frombuffer(raw, dtype='<i2').astype(np.float32)/32768
                if not np.isfinite(values).all() or samples+len(values) > 320000: raise Refused('ctc_input_samples')
                first_input = first_input or time.monotonic()
                samples += len(values); sha.update(raw)
                audio.accept_waveform(16000, values); drain()
                send(stream, ACK, sequence, struct.pack('!I', len(values)))
            elif kind == END:
                declared = json.loads(raw)
                if declared != dict(samples=samples, sha256=sha.hexdigest()): raise Refused('ctc_input_integrity')
                flush = time.monotonic()
                audio.accept_waveform(16000, np.zeros(10560, dtype=np.float32))
                audio.input_finished(); drain()
                result = recognizer.get_result(audio)
                if not isinstance(result, str) or len(result)>1000: raise Refused('ctc_result_type')
                ended = time.monotonic()
                import resource
                value = dict(real_samples=samples, tail_zero_samples=10560, tail_wait_ms=0,
                    final_mono=ended, final_flush_ms=(ended-flush)*1000, decode_calls=len(calls),
                    decode_wall_ms=sum(calls), decode_cpu_ms=cpu_ms, decode_call_max_ms=max(calls, default=0),
                    decode_call_p95_ms=sorted(calls)[max(0, int(len(calls)*.95)-1)] if calls else 0,
                    public_result_sha256=hashlib.sha256(result.encode()).hexdigest(), public_result_chars=len(result),
                    peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                    threads=1, model_constructions=1, gold_accuracy_passed=False)
                send(stream, RESULT, sequence, json.dumps(value).encode()); return 0
            else: raise Refused('ctc_input_kind')
    except Exception:
        try: send(stream, FAILED, 0, b'')
        except OSError: pass
        return 1
    finally: stream.close()


def run(args):
    guard = load('_coexist_guard', args.guard_source, GUARD_SHA)
    before = guard.metadata(args)
    pipeline = load('_original_public_pipeline', args.pipeline_source, args.pipeline_sha256)
    code = Path(args.runtime_root)/'runtime/aura'
    pins = json.loads((Path(args.runtime_root)/'startup/config.json').read_bytes())['component_sha256']
    names = ('board_capture.py', 'board_pcm_queue.py', 'automatic_capture.py', 'board_gtcrn_fft.py',
             'board_gtcrn_reuse.py', 'board_asr_frontend.py')
    for name in names:
        rel = 'board/runtime/audio/'+name
        if digest(code/rel) != pins[rel]: raise Refused('production_component_changed')
    if digest(args.wav) != args.wav_sha256: raise Refused('public_wave_pin_changed')
    ctc_root = Path(args.ctc_root)
    if (digest(ctc_root/'model.int8.onnx') != CTC_MODEL_SHA
            or digest(ctc_root/'tokens.txt') != CTC_TOKEN_SHA):
        raise Refused('ctc_model_pin_changed')
    if not args.run:
        return dict(status='INSPECT_ONLY_NO_MODEL', before=before, raw_queue_frames=8,
                    asr_pending_samples=16000, extra_frontend_resident=True, extra_ctc_resident=True)
    sys.path[:0] = [str(code), '/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps',
                   '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps']
    import numpy as np
    import onnxruntime as ort
    import sherpa_onnx as sherpa
    if (np.__version__, ort.__version__, sherpa.__version__) != ('1.21.2', '1.17.3', '1.13.8'):
        raise Refused('production_dependency_versions_changed')
    from board.runtime.audio.board_capture import BoardAutomaticCapture, BoardFrontendPool
    from board.runtime.audio.board_gtcrn_reuse import ReuseFftSpeechGate
    with wave.open(args.wav, 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1,2,16000):
            raise Refused('public_wave_format')
        pcm = wav.readframes(wav.getnframes())
    if not pcm or len(pcm)>18*32000: raise Refused('public_wave_budget')
    framed = pcm+bytes((-len(pcm))%640)+bytes(640*70)
    source = pipeline.PacedPublicPcm(framed)
    parent, child = socket.socketpair(); parent.settimeout(45.)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--ctc-fd', str(child.fileno()), '--ctc-root', args.ctc_root]
    environment = dict(os.environ, PYTHONPATH='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.Popen(command, pass_fds=(child.fileno(),), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=environment)
    child.close(); sink = pool = capture = None; timings = []; priority = pipeline.ProbeProcessPriority(-10)
    try:
        kind, seq, ready = receive(parent)
        if kind != READY or seq != 0: raise Refused('ctc_startup_failed')
        parent.settimeout(3.); sink = AsyncCtcSink(parent)
        with priority:
            gate = ReuseFftSpeechGate(args.frontend_directory, num_threads=1, buffer_reuse=True, io_binding=True)
            pool = BoardFrontendPool(gate)
            class Observed:
                def __init__(self): self.lease = pool.acquire()
                def __call__(self, frame):
                    began, cpu = time.monotonic(), time.thread_time()
                    try: return self.lease(frame)
                    finally: timings.append(((time.monotonic()-began)*1000, (time.thread_time()-cpu)*1000))
                def close(self): self.lease.close()
                def public(self): return self.lease.public()
            def no_device(*a, **kw): raise Refused('microphone_forbidden')
            capture = BoardAutomaticCapture(lambda: False, max_seconds=20, frontend_factory=Observed, process_factory=no_device)
            capture.frontend_queue_frames = 8; capture.endpoint = capture._endpoint()
            attach_raw_tap(capture.endpoint, sink)
            capture._signal = lambda *_: source.stop()
            started = time.monotonic()
            captured = capture._read_pcm(SimpleNamespace(stdout=source))
            endpoint_end = time.monotonic()
            queue = capture._board_pcm_input.public()
            offset = capture.endpoint.start_sample*2
            if (not captured or captured != framed[offset:offset+len(captured)] or queue['error']):
                raise Refused('original_capture_integrity_failed')
            result = sink.finish()
        after = guard.metadata(args, allow_background=True)
        if before['ui'] != after['ui'] or before['camera'] != after['camera']: raise Refused('production_owner_changed')
        background = before['memory'] != after['memory'] or not after['model_idle']
        return dict(status='PUBLIC_COEXIST_MEASURED_NOT_PRODUCTION_ACCEPTANCE', before=before, after=after,
            background_changed=background, raw_input_queue=queue, ctc_transport=sink.public(), ctc=result,
            source_supply_lateness_max_ms=max(source.lateness_ms, default=0), ctc_startup=json.loads(ready),
            frontend_frames=len(timings), frontend_wall_mean_ms=sum(v[0] for v in timings)/len(timings),
            frontend_wall_max_ms=max(v[0] for v in timings), frontend_cpu_mean_ms=sum(v[1] for v in timings)/len(timings),
            final_after_endpoint_ms=(result['final_mono']-endpoint_end)*1000,
            final_after_scheduled_source_end_ms=(result['final_mono']-source.origin-len(pcm)/32000)*1000,
            captured_samples=len(captured)//2, capture_start_sample=capture.endpoint.start_sample,
            captured_pcm_sha256=hashlib.sha256(captured).hexdigest(),
            raw_capture_preserved=True, ctc_input='original RAW PCM16; GTCRN/Silero VAD path unchanged',
            ctc_feed_window='all RAW frames until original endpoint; not a production pre-roll/ticket bridge',
            original_gtcrn_output_lag_samples=gate.frames*320-gate.samples,
            extra_frontend_resident=True, production_frontend_also_resident=True,
            actual_render_fps_acceptance=False, microphone_opened=False, physical_playback=False,
            production_db_accessed=False, production_changed=False, priority=priority.record)
    except Exception as error:
        return dict(status='PUBLIC_COEXIST_FAILED', error_code=error.args[0] if isinstance(error, Refused) else type(error).__name__,
            input_queue=getattr(capture, '_board_pcm_input', None).public() if getattr(capture, '_board_pcm_input', None) else None,
            ctc_transport=sink.public() if sink else None, production_changed=False,
            frontend_frames=len(timings), frontend_wall_max_ms=max((v[0] for v in timings), default=0),
            frontend_cpu_mean_ms=sum(v[1] for v in timings)/len(timings) if timings else None)
    finally:
        source.stop()
        if capture is not None:
            pump = getattr(capture, '_board_pcm_input', None)
            if pump is not None: pump.close()
            capture._close_endpoint()
            if capture._timer is not None: capture._timer.cancel()
        if pool is not None: pool.close()
        if sink is not None: sink.close()
        else: parent.close()
        try: process.wait(timeout=1.)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=2.)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=2.)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ctc-fd', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--ctc-root', default='/home/root/aura-public-streaming-asr-20261031/68c9c943840f7d9c')
    parser.add_argument('--guard-source', default='/home/root/aura-public-asr-thread-abba-20261031/210925ca35fb5acd/probe_asr_abba.py')
    parser.add_argument('--pipeline-source')
    parser.add_argument('--pipeline-sha256')
    parser.add_argument('--runtime-root', default='/home/root/aura-board-business-20261030/production-5259eab11e42af13')
    parser.add_argument('--startup-sha256', default='39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a')
    parser.add_argument('--boot-id')
    for name in ('ui-pid', 'ui-birth', 'camera-pid', 'camera-birth'): parser.add_argument('--'+name, type=int)
    parser.add_argument('--min-available-mib', type=int, default=1500)
    parser.add_argument('--frontend-directory', default='/home/root/aura-board-owner-candidate-20261030/frontend-b3d06b653876469d/models')
    parser.add_argument('--wav', default='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav')
    parser.add_argument('--wav-sha256', default='1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.ctc_fd is not None: return ctc_worker(args.ctc_fd, args.ctc_root)
    if not args.pipeline_source or not args.pipeline_sha256 or args.min_available_mib < 512:
        parser.error('require pinned public pipeline source and explicit memory margin')
    value = run(args); print(json.dumps(value, allow_nan=False))
    return 0 if value['status'] != 'PUBLIC_COEXIST_FAILED' else 1


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception:
        print('{"status":"REFUSED","error_code":"coexist_preflight_failed"}')
        raise SystemExit(1)
