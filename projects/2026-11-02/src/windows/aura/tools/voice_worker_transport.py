"""Deadline-bound transport for one owned speech subprocess.

A stdout reader is local to a process generation. Partial lines cannot block
the request owner; failed/cancelled requests retire that exact process before
the next request can start. No PID discovered from a file is ever terminated.
"""
import json
import math
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid
from tools.owned_speech_process import OwnedSpeechJob


class BoundedSpeechProcess:
    MAX_LINE = 1024 * 1024

    def __init__(self, command, log_path, *, max_line=None):
        self.command = command
        self.log_path = Path(log_path) if log_path is not None else None
        if max_line is not None:
            if type(max_line) is not int or not 1024<=max_line<=8*1024*1024:
                raise ValueError('Invalid speech response limit')
            self.MAX_LINE=max_line
        self.process = None
        self.log = None
        self.lock = threading.Lock()
        self.guard = threading.RLock()
        self.active_id = None
        self.reader = None
        self.writer = None
        self.messages = None
        self.closed = False
        self.quarantined = False
        self.error = ''
        self.job = None

    def _start(self):
        with self.guard:
            if self.closed:
                raise RuntimeError('Speech worker is closed')
            if self.process is not None and self.process.poll() is None:
                if self.quarantined:
                    raise RuntimeError('Previous speech worker termination is not confirmed')
                return self.process, self.messages
            if self.log:
                self.log.close()
            if self.job:
                self.job.close()
                self.job=None
            self.log = self.log_path.open('a', encoding='utf-8') if self.log_path is not None else None
            self.process = subprocess.Popen(self.command(), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=self.log if self.log is not None else subprocess.DEVNULL,
                text=True, encoding='utf-8',
                bufsize=1, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            process = self.process
            try:
                self.job=OwnedSpeechJob(process)
            except BaseException:
                process.terminate()
                process.wait(timeout=1)
                raise
            messages = self.messages = queue.Queue(maxsize=8)
            self.quarantined = False

            def deliver(value):
                while process.poll() is None:
                    try:
                        messages.put(value, timeout=.05)
                        return
                    except queue.Full:
                        continue
                try:
                    messages.put_nowait(value)
                except queue.Full:
                    pass

            def read():
                try:
                    while True:
                        line = process.stdout.readline(self.MAX_LINE + 1)
                        if not line:
                            deliver(('error', 'Speech worker stopped before returning a result'))
                            return
                        if len(line) > self.MAX_LINE:
                            deliver(('error', 'Speech worker response exceeds size limit'))
                            return
                        if line.startswith('RESULT '):
                            try:
                                value = json.loads(line[7:])
                            except (TypeError, ValueError):
                                deliver(('error', 'Invalid speech worker JSON response'))
                                return
                            deliver(('result', value))
                            # The idle reader must not retain the last PCM
                            # response (or its serialized line) between jobs.
                            value = None
                        line = None
                except (OSError, ValueError) as exc:
                    deliver(('error', 'Speech worker output failed: ' + type(exc).__name__))

            self.reader = threading.Thread(target=read, daemon=True, name='aura-speech-result')
            self.reader.start()
            return process, messages

    @staticmethod
    def _check(deadline, cancelled):
        if cancelled is not None and cancelled.is_set():
            raise InterruptedError('Speech request cancelled')
        if time.monotonic() >= deadline:
            raise TimeoutError('Speech worker deadline expired')

    def _retire(self, process, reason, *, expected_id=None):
        with self.guard:
            if process is not self.process or (expected_id is not None and self.active_id != expected_id):
                return False
            self.quarantined = True
            self.error = reason
            reader = self.reader
            writer = self.writer
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=.35)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=.35)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            except OSError:
                pass
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=.2)
        if writer is not None and writer is not threading.current_thread():
            writer.join(timeout=.2)
        if process.poll() is not None:
            # Never close a TextIOWrapper while another thread is blocked in
            # its read lock. Process termination normally produces EOF first.
            if reader is None or not reader.is_alive():
                for handle in (process.stdout,):
                    if handle:
                        try:
                            handle.close()
                        except OSError:
                            pass
            if writer is None or not writer.is_alive():
                try:process.stdin.close()
                except (OSError, ValueError):pass
            return True
        return False

    def request(self, request, *, deadline=None, timeout=120., cancelled=None, request_id=None):
        if deadline is None:
            if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
                raise ValueError('Require a finite positive speech timeout')
            deadline = time.monotonic() + timeout
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Require a finite speech deadline')
        token = request_id or uuid.uuid4().hex
        if not isinstance(token, str) or not token or len(token) > 256:
            raise ValueError('Invalid speech request identifier')
        payload = dict(request, request_id=token)
        encoded = json.dumps(payload, ensure_ascii=False) + '\n'
        if len(encoded.encode('utf-8')) > 8192:
            raise ValueError('Speech request exceeds size limit')
        while True:
            self._check(deadline, cancelled)
            if self.lock.acquire(timeout=min(.05, max(.001, deadline-time.monotonic()))):
                break
        process = None
        try:
            self._check(deadline, cancelled)
            process, messages = self._start()
            with self.guard:
                self.active_id = token
            write_done = threading.Event()
            write_errors = []
            def write():
                try:
                    process.stdin.write(encoded)
                    process.stdin.flush()
                except (OSError, ValueError) as exc:
                    write_errors.append(exc)
                finally:
                    write_done.set()
            self.writer = threading.Thread(target=write, daemon=True, name='aura-speech-request')
            self.writer.start()
            while not write_done.wait(timeout=min(.05, max(.001, deadline-time.monotonic()))):
                self._check(deadline, cancelled)
                if self.closed:raise InterruptedError('Speech worker closed')
            self._check(deadline, cancelled)
            if write_errors:raise RuntimeError('Speech worker input failed: ' + type(write_errors[0]).__name__)
            while True:
                self._check(deadline, cancelled)
                if self.closed:
                    raise InterruptedError('Speech worker closed')
                try:
                    kind, value = messages.get(timeout=min(.05, max(.001, deadline-time.monotonic())))
                except queue.Empty:
                    if process.poll() is not None:
                        raise RuntimeError('Speech worker exited without a result')
                    continue
                self._check(deadline, cancelled)
                if kind == 'error':
                    raise RuntimeError(value)
                if not isinstance(value, dict) or value.get('request_id') != token:
                    raise RuntimeError('Speech worker result belongs to another request')
                if value.get('ok') is not True:
                    raise RuntimeError(str(value.get('error', 'Speech synthesis failed'))[:500])
                if not isinstance(value.get('result'), dict):
                    raise RuntimeError('Invalid speech worker result payload')
                with self.guard:
                    self.error = ''
                return value['result']
        except BaseException as exc:
            if process is not None:
                self._retire(process, type(exc).__name__ + ': ' + str(exc)[:300])
            raise
        finally:
            with self.guard:
                if self.active_id == token:
                    self.active_id = None
            self.lock.release()

    def cancel_request(self, request_id):
        with self.guard:
            if self.active_id != request_id or self.process is None:
                return False
            process = self.process
        return self._retire(process, 'Speech request cancelled', expected_id=request_id)

    def health(self):
        with self.guard:
            alive = self.process is not None and self.process.poll() is None
            return {'alive': alive, 'request_active': self.active_id is not None,
                    'quarantined': self.quarantined, 'closed': self.closed,
                    'error': self.error}

    def close(self):
        with self.guard:
            self.closed = True
            process = self.process
        if process is not None:
            self._retire(process, 'Speech worker closed')
        if self.job:
            self.job.close()
            self.job=None
        if self.log and (process is None or process.poll() is not None):
            self.log.close()
