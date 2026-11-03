"""One explicitly selected frontend model in an owned subprocess; fixed local IPC only.

Importing this module is inert. BoardProcessSpeechGate explicitly starts one
child before any audio owner. No parent model, network listener, file audio or
alternate inference/endpoint path is constructed.
"""
import argparse
import math
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import threading
import time


MAGIC = b'AFG1'
HEADER = struct.Struct('!4sBBHQQI')
RESULT = struct.Struct('!HBBQQ8dIi')
FRAME, RESET_DENOISER, RESET_VAD, STOP, HELLO = 1, 2, 3, 4, 5
OK, INIT_FAILED, PROTOCOL_FAILED, FRAME_FAILED, COMPUTE_FAILED, PRIORITY_FAILED = range(6)
FRAME_BYTES = 320 * 4
MAX_PAYLOAD = FRAME_BYTES
_KINDS = (FRAME, RESET_DENOISER, RESET_VAD, STOP, HELLO) + tuple(range(6,12))
MODE_BUSY = 6

def _payload_limit(kind):
    if kind == (9 | 128):return 640000 + 4096 + 4
    if kind in tuple(k | 128 for k in range(7,12)):return 4096
    return MAX_PAYLOAD
_ERRORS = {INIT_FAILED:'frontend_worker_initialization_failed',
           PROTOCOL_FAILED:'frontend_worker_protocol_failed',
           FRAME_FAILED:'frontend_worker_invalid_frame',
           COMPUTE_FAILED:'frontend_worker_compute_failed',
           PRIORITY_FAILED:'frontend_worker_priority_rejected'}


class FrontendProcessError(RuntimeError):
    pass


class FrontendModeBusy(ValueError):
    pass


class _Cancelled(InterruptedError):
    pass


class _Channel:
    """Stateful partial-message buffer; at most one fixed frame plus header."""
    def __init__(self, stream, clock=time.monotonic):
        self.stream, self.clock = stream, clock
        self.buffer = bytearray()

    def send(self, kind, generation, sequence, payload, deadline):
        if len(payload) > _payload_limit(kind):
            raise FrontendProcessError('frontend_worker_payload_limit')
        packet = HEADER.pack(MAGIC, 1, kind, 0, generation, sequence, len(payload)) + payload
        offset = 0
        while offset < len(packet):
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise FrontendProcessError('frontend_worker_write_timeout')
            self.stream.settimeout(min(.02, remaining))
            try:
                sent = self.stream.send(packet[offset:])
            except socket.timeout:
                continue
            if sent <= 0:
                raise FrontendProcessError('frontend_worker_disconnected')
            offset += sent

    def receive(self, deadline, cancelled=lambda:False, poll_interval=.02):
        while True:
            if cancelled():
                raise _Cancelled('frontend_worker_capture_cancelled')
            needed = HEADER.size
            if len(self.buffer) >= HEADER.size:
                magic, version, kind, reserved, generation, sequence, size = HEADER.unpack_from(self.buffer)
                if (magic != MAGIC or version != 1 or reserved or size > _payload_limit(kind)
                        or kind not in _KINDS + tuple(k | 128 for k in _KINDS)):
                    raise FrontendProcessError('frontend_worker_protocol_failed')
                needed += size
                if len(self.buffer) >= needed:
                    payload = bytes(self.buffer[HEADER.size:needed])
                    del self.buffer[:needed]
                    return kind, generation, sequence, payload
            remaining = poll_interval if deadline is None else deadline - self.clock()
            if remaining <= 0:
                raise FrontendProcessError('frontend_worker_read_timeout')
            self.stream.settimeout(min(poll_interval, remaining))
            try:
                block = self.stream.recv(needed - len(self.buffer))
            except socket.timeout:
                continue
            if not block:
                raise FrontendProcessError('frontend_worker_disconnected')
            self.buffer.extend(block)


def _result(code=OK, decision=False, gate=None, timing=None, nice=-10):
    timing = timing or [0.] * 6
    return RESULT.pack(code, bool(decision), 0,
        getattr(gate, 'frames', 0), getattr(gate, 'samples', 0),
        float(getattr(gate, 'last_ms', 0.) or 0.), float(getattr(gate, 'max_ms', 0.)),
        *timing, os.getpid(), nice)


def serve(stream, gate_factory, *, apply_priority=None, clock=time.monotonic,
          thread_clock=time.thread_time, priority_reader=None, auto_capture_factory=None):
    from board.runtime.audio.board_frontend_auto import serve_shared
    return serve_shared(stream,gate_factory,apply_priority=apply_priority,clock=clock,
        thread_clock=thread_clock,priority_reader=priority_reader,auto_capture_factory=auto_capture_factory)


class _Reset:
    def __init__(self, owner, kind):
        self.owner, self.kind = owner, kind
    def reset(self):
        self.owner._reset(self.kind)


class BoardProcessSpeechGate:
    """BoardFrontendPool-compatible proxy. close() cancels; shutdown() exits."""
    def __init__(self, directory, *, num_threads=1, process_factory=subprocess.Popen,
                 clock=time.monotonic, startup_timeout=60., frame_timeout=.5, optimization='baseline'):
        if type(num_threads) is not int or num_threads != 1:
            raise ValueError('The frontend worker requires one model thread')
        if type(optimization) is not str or optimization not in ('baseline', 'combined'):
            raise ValueError('Choose explicit baseline or reviewed combined frontend')
        self.optimization = optimization
        if not 0 < startup_timeout <= 90 or not .05 <= frame_timeout <= 2:
            raise ValueError('Bounded frontend IPC timeouts required')
        import numpy as np
        self.np, self.clock, self.frame_timeout = np, clock, frame_timeout
        self.lock, self._io_lock = threading.Lock(), threading.Lock()
        self.denoiser, self.vad = _Reset(self, RESET_DENOISER), _Reset(self, RESET_VAD)
        self.frames = self.samples = 0
        self.last_ms = None
        self.max_ms = 0.
        self.closed = True
        self.error = ''
        self._generation = self._sequence = 0
        self._abandoned = set()
        self._shutdown = False
        self._metrics = {}
        self._rpc_last_ms = self._rpc_max_ms = self._rpc_total_ms = 0.
        self.process = None
        parent, child = socket.socketpair()
        self._channel = _Channel(parent, clock)
        entry = Path(__file__).resolve()
        env = dict(os.environ)
        aura = str(entry.parents[3])
        env['PYTHONPATH'] = aura + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
            env[key] = '1'
        env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
        try:
            self.process = process_factory([sys.executable, '-B', str(entry), '--worker-fd', str(child.fileno()),
                '--frontend-directory', str(directory), '--parent-pid', str(os.getpid()),
                '--frontend-optimization', optimization],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                pass_fds=(child.fileno(),), close_fds=True, env=env)
            child.close()
            kind, generation, sequence, payload = self._channel.receive(clock() + startup_timeout)
            if (kind, generation, sequence) != (HELLO | 128, 0, 0):
                raise FrontendProcessError('frontend_worker_protocol_failed')
            self._accept(payload)
        except BaseException:
            child.close()
            self.shutdown(timeout=1.)
            raise

    def _accept(self, payload, *, cancelled_frame=False):
        if len(payload) != RESULT.size:
            raise FrontendProcessError('frontend_worker_protocol_failed')
        code, decision, reserved, frames, samples, *values = RESULT.unpack(payload)
        numbers, pid, nice = values[:-2], values[-2], values[-1]
        if code == MODE_BUSY:
            raise FrontendModeBusy('frontend_auto_mode_busy')
        if code:
            raise FrontendProcessError(_ERRORS.get(code, 'frontend_worker_protocol_failed'))
        if nice != -10:
            raise FrontendProcessError('frontend_worker_priority_rejected')
        if (decision not in (0, 1) or reserved or pid != self.process.pid
                or any(not math.isfinite(x) or x < 0 for x in numbers)
                # Cancellation may advance the native model by one frame
                # before its completed-frame counter is published. Only
                # closed control receipts may carry that bounded residue.
                or not (-320 if cancelled_frame else 0) <= frames * 320 - samples <= 1024):
            raise FrontendProcessError('frontend_worker_protocol_failed')
        self.frames, self.samples = frames, samples
        self.last_ms, self.max_ms = numbers[:2]
        self._metrics = dict(zip(('worker_frame_wall_last_ms', 'worker_frame_wall_max_ms',
            'worker_frame_wall_total_ms', 'worker_frame_cpu_last_ms',
            'worker_frame_cpu_max_ms', 'worker_frame_cpu_total_ms'), numbers[2:]))
        return bool(decision)

    def _rpc(self, kind, *, payload=b'', generation=None, cancellable=False, timeout=None, decoder=None):
        generation = self._generation if generation is None else generation
        deadline = self.clock() + (self.frame_timeout if timeout is None else timeout)
        with self._io_lock:
            if self._shutdown or self.process is None or self.process.poll() is not None:
                raise FrontendProcessError('frontend_worker_not_alive')
            if self.error and kind != STOP:
                raise FrontendProcessError(self.error)
            cancelled = lambda: cancellable and (self.closed or self._generation != generation)
            if cancelled():
                raise _Cancelled('frontend_worker_capture_cancelled')
            self._sequence += 1
            sequence = self._sequence
            started = self.clock()
            awaiting = False
            try:
                self._channel.send(kind, generation, sequence, payload, deadline)
                awaiting = True
                while True:
                    response, current, received, data = self._channel.receive(deadline, cancelled)
                    key = (response, current, received)
                    if key in self._abandoned:
                        self._abandoned.remove(key)  # Discard cancelled generation's complete result.
                        continue
                    if key != (kind | 128, generation, sequence):
                        raise FrontendProcessError('frontend_worker_response_owner_mismatch')
                    awaiting = False
                    if cancelled():
                        raise _Cancelled('frontend_worker_capture_cancelled')
                    decision = decoder(data) if decoder is not None else self._accept(data,
                        cancelled_frame=kind in (STOP, 6))  # 6 is closed GATE_RELEASE, never FRAME.
                    elapsed = (self.clock() - started) * 1000.
                    self._rpc_last_ms, self._rpc_max_ms = elapsed, max(self._rpc_max_ms, elapsed)
                    self._rpc_total_ms += elapsed
                    return decision
            except _Cancelled:
                if awaiting:
                    self._abandoned.add((kind | 128, generation, sequence))
                if len(self._abandoned) > 2:
                    self.error = 'frontend_worker_cancelled_response_limit'
                raise
            except (OSError, FrontendProcessError) as exc:
                self.error = str(exc) if isinstance(exc, FrontendProcessError) else 'frontend_worker_ipc_failed'
                self.closed = True
                raise FrontendProcessError(self.error) from None

    def _reset(self, kind):
        if kind == RESET_DENOISER:
            self._generation += 1
        try:
            self._rpc(kind)
        except FrontendModeBusy:
            if kind == RESET_DENOISER:self._generation -= 1
            raise
        if kind == RESET_VAD:
            self._rpc_last_ms = self._rpc_max_ms = self._rpc_total_ms = 0.

    def __call__(self, frame):
        if self.closed or self.error:
            raise FrontendProcessError(self.error or 'frontend_worker_capture_closed')
        values = self.np.asarray(frame, dtype=self.np.float32)
        if values.shape != (320,) or not self.np.isfinite(values).all() or self.np.max(self.np.abs(values)) > 1:
            raise ValueError('Board frontend requires normalized 20 ms/16 kHz mono frames')
        if not self.lock.acquire(blocking=False):
            raise FrontendProcessError('frontend_worker_busy')
        try:
            return self._rpc(FRAME, payload=values.astype('<f4', copy=False).tobytes(), cancellable=True)
        finally:
            self.lock.release()

    def close(self):
        self.closed = True  # Atomic cancellation flag; child/model stays available for reset.

    def public(self):
        return dict(enabled=True, backend='gtcrn-numpy-fft-silero-v5-board-process',
            frontend_optimization=self.optimization,
            frames=self.frames, processed_samples=self.samples, closed=self.closed, error=self.error,
            last_roundtrip_ms=self.last_ms, max_roundtrip_ms=self.max_ms,
            worker_process_alive=bool(self.process and self.process.poll() is None),
            worker_pid=self.process.pid if self.process else None, worker_nice=-10,
            worker_generation=self._generation, ipc_rpc_last_ms=self._rpc_last_ms,
            ipc_rpc_max_ms=self._rpc_max_ms, ipc_rpc_total_ms=self._rpc_total_ms, **self._metrics)

    def shutdown(self, timeout=8.):
        """Owned child only: graceful IPC, then bounded TERM; never force-kill."""
        self.close()
        if self._shutdown:
            return self.process is None or self.process.poll() is not None
        process = self.process
        if process is not None and process.poll() is None:
            if self._io_lock.acquire(timeout=min(.25, timeout)):
                self._io_lock.release()
                try:
                    self._rpc(STOP, timeout=min(6., timeout))
                except (OSError, FrontendProcessError):
                    pass
            try:
                process.wait(timeout=min(.5, timeout))
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=min(.75, timeout))
                except subprocess.TimeoutExpired:
                    return False
        self._shutdown = True
        self._channel.stream.close()
        return True


def _worker_main():
    if len(sys.argv)>1 and sys.argv[1]=='--exec-arecord-parent':
        from board.runtime.audio.board_frontend_auto import exec_arecord_parent
        if len(sys.argv)<6 or sys.argv[3]!='--':raise SystemExit(2)
        exec_arecord_parent(int(sys.argv[2]),sys.argv[4:])
        return
    parser = argparse.ArgumentParser(description='Owned explicit-mode frontend socketpair child')
    parser.add_argument('--worker-fd', required=True, type=int)
    parser.add_argument('--frontend-directory', required=True)
    parser.add_argument('--frontend-optimization', choices=('baseline','combined'), default='baseline')
    parser.add_argument('--parent-pid', required=True, type=int)
    args = parser.parse_args()
    if args.worker_fd < 3 or args.parent_pid != os.getppid():
        raise SystemExit(2)
    stream = socket.socket(fileno=args.worker_fd)
    if stream.family != socket.AF_UNIX or stream.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_STREAM:
        stream.close()
        raise SystemExit(2)
    def priority():
        os.setpriority(os.PRIO_PROCESS, 0, -10)
        if os.getpriority(os.PRIO_PROCESS, 0) != -10:
            raise RuntimeError('Worker priority rejected')
    def create():
        if os.getppid() != args.parent_pid:
            raise RuntimeError('Frontend owner disappeared')
        if args.frontend_optimization == 'combined':
            from board.runtime.audio.board_gtcrn_reuse import ReuseFftSpeechGate
            return ReuseFftSpeechGate(args.frontend_directory, num_threads=1,
                                      buffer_reuse=True, io_binding=True)
        from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate
        return BoardFftSpeechGate(args.frontend_directory, num_threads=1)
    serve(stream, create, apply_priority=priority,
          priority_reader=lambda:os.getpriority(os.PRIO_PROCESS, 0))


if __name__ == '__main__':
    _worker_main()
