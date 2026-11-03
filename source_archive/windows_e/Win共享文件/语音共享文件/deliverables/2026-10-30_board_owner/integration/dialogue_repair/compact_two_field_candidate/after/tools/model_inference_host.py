"""Candidate Windows-only model executor. Never opens a business store.

The board sends complete prompts and separately selects the text to speak.
There is no ASR, identity, memory, reply policy, playback or prompt history here.
Start explicitly; importing this module does not start a model or a service.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
import os
from pathlib import Path
import select
import shlex
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from common.model_inference_wire import (MAX_BODY, MAX_OUTPUT_BYTES, MAX_RESPONSE,
    Owner, WireError, decode_audio, make_response, validate_request, validate_response)


@dataclass
class _Job:
    kind: str
    owner: Owner
    payload: dict
    deadline: float
    cancelled: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    reason: str = ''
    response: object = None
    status: int = 200

    @property
    def summary(self):
        return self.kind == 'llm' and self.payload.get('task') == 'summary'


class InferenceHost:
    """One bounded execution lane; foreground cancels active/queued summary.

    backend.llm(payload, *, deadline, cancelled) -> {text, metrics?}
    backend.tts(payload, *, deadline, cancelled) -> {audio: wire audio object}
    A backend must obey the original absolute monotonic deadline. Cancellation
    may finish already-started TTS within that deadline; results are discarded.
    No response cache is retained. Completed request IDs have bounded metadata
    tombstones (256 by default); clients must never reuse IDs, including retries.
    """
    def __init__(self, backend, *, max_pending=8, max_seen=256, max_owners=128,
                 clock=time.monotonic):
        for value in (max_pending, max_seen, max_owners):
            if type(value) is not int or not 1 <= value <= 4096:
                raise ValueError('Invalid inference capacity')
        self.backend, self.clock = backend, clock
        self.max_pending, self.max_seen, self.max_owners = max_pending, max_seen, max_owners
        self.condition = threading.Condition()
        self.jobs, self.seen, self.generations = {}, OrderedDict(), OrderedDict()
        self.pending, self.active = [], None
        self.counts = Counter()
        self.closed = False
        self.worker = threading.Thread(target=self._run, daemon=True, name='aura-model-inference')
        self.worker.start()

    def _cancel_locked(self, job, reason):
        if job.done.is_set():
            return False
        job.reason = reason
        job.cancelled.set()
        job.status = 504 if reason == 'deadline_exceeded' else 409
        job.response = make_response(job.owner, error=reason, retryable=reason == 'preempted')
        job.done.set()
        self.counts[reason] += 1
        return True

    def _forget_locked(self, job):
        self.jobs.pop(job.owner.request_id, None)
        self.seen[job.owner.request_id] = job.owner
        self.seen.move_to_end(job.owner.request_id)
        while len(self.seen) > self.max_seen:
            self.seen.popitem(last=False)
        # Request text, model text and PCM are never placed in a tombstone.
        job.payload.clear()

    def _trim_pending_locked(self):
        remaining = []
        for job in self.pending:
            if self.clock() >= job.deadline:
                self._cancel_locked(job, 'deadline_exceeded')
            if job.done.is_set():
                self._forget_locked(job)
            else:
                remaining.append(job)
        self.pending = remaining

    def handle(self, kind, payload, received_at=None):
        """Blocking request API returning (HTTP status, JSON response)."""
        received_at = self.clock() if received_at is None else received_at
        owner = None
        try:
            owner = Owner.from_dict(payload)
            request = validate_request(kind, payload)
        except WireError as exc:
            # Malformed ownership cannot safely be echoed as trusted ownership.
            body = make_response(owner, error=exc.code) if owner is not None else {
                'protocol_version': 1, 'ok': False,
                'error': {'code': exc.code, 'retryable': False}}
            return 400, body
        with self.condition:
            if self.closed:
                return 503, make_response(owner, error='service_closed', retryable=True)
            self._trim_pending_locked()
            if kind == 'cancel':
                target = self.jobs.get(owner.request_id)
                if target is not None and target.owner == owner:
                    changed = self._cancel_locked(target, 'cancelled')
                    self.condition.notify_all()
                    return 200, make_response(owner, result={'cancelled': changed, 'state': 'cancelled'})
                if self.seen.get(owner.request_id) == owner:
                    return 200, make_response(owner, result={'cancelled': False, 'state': 'completed'})
                return 404, make_response(owner, error='request_not_found')
            if ((kind == 'warmup' and self.jobs)
                    or (kind != 'warmup' and any(old.kind == 'warmup' for old in self.jobs.values()))):
                return 503, make_response(owner, error='startup_busy', retryable=True)
            if owner.request_id in self.jobs or owner.request_id in self.seen:
                return 409, make_response(owner, error='duplicate_request')
            latest = self.generations.get(owner.session_key)
            if latest is not None and owner.generation < latest:
                return 409, make_response(owner, error='stale_generation')
            if latest is None and len(self.generations) >= self.max_owners:
                # Do not evict generation guards for active owners. Fail closed
                # at capacity; host restart also resets this transport epoch.
                return 503, make_response(owner, error='owner_capacity', retryable=True)
            deadline = received_at + request['budget_ms'] / 1000
            if not math.isfinite(received_at) or deadline <= self.clock():
                return 504, make_response(owner, error='deadline_exceeded')
            if (kind == 'llm' and request['task'] == 'summary'
                    and any(not old.summary for old in self.jobs.values())):
                # Even a newer generation of background work cannot cancel
                # foreground work or claim its place in the execution lane.
                return 503, make_response(owner, error='foreground_busy', retryable=True)
            if latest is not None and owner.generation > latest:
                for old in tuple(self.jobs.values()):
                    if old.owner.session_key == owner.session_key and old.owner.generation < owner.generation:
                        self._cancel_locked(old, 'superseded')
            foreground = kind in ('tts', 'warmup') or request['task'] == 'dialogue'
            if foreground:
                for old in tuple(self.jobs.values()):
                    if old.summary:
                        self._cancel_locked(old, 'preempted')
            self._trim_pending_locked()
            if len(self.jobs) >= self.max_pending + 1:
                return 503, make_response(owner, error='queue_full', retryable=True)
            self.generations[owner.session_key] = owner.generation
            job = _Job(kind, owner, request, deadline)
            self.jobs[owner.request_id] = job
            self.pending.append(job)
            self.counts['accepted_' + kind] += 1
            self.condition.notify_all()
        while not job.done.wait(.02):
            with self.condition:
                if self.clock() >= deadline:
                    self._cancel_locked(job, 'deadline_exceeded')
                    self.condition.notify_all()
        return job.status, job.response

    def _run(self):
        while True:
            with self.condition:
                self._trim_pending_locked()
                while not self.pending and not self.closed:
                    self.condition.wait(.1)
                    self._trim_pending_locked()
                if self.closed:
                    return
                # Foreground FIFO precedes low-priority summary FIFO.
                index = next((i for i, row in enumerate(self.pending) if not row.summary), 0)
                job = self.pending.pop(index)
                self.active = job
            try:
                if job.cancelled.is_set():
                    raise InterruptedError()
                result = getattr(self.backend, job.kind)(job.payload,
                    deadline=job.deadline, cancelled=job.cancelled)
                candidate = make_response(job.owner, result=result)
                validate_response(candidate, job.owner, job.kind)
                status, response = 200, candidate
            except InterruptedError:
                status, response = 409, make_response(job.owner, error=job.reason or 'cancelled')
            except TimeoutError:
                status, response = 504, make_response(job.owner, error='deadline_exceeded')
            except Exception as exc:
                # Exception strings may contain prompts/audio or backend paths.
                # Public responses and counters carry a small static code only.
                from common.gpu_coordination import GpuBusy
                from common.inference_output_contract import OutputTruncated
                code = ('backend_output_truncated' if isinstance(exc, OutputTruncated) else
                        'gpu_busy' if isinstance(exc, GpuBusy) else
                        'tts_owner_conflict' if isinstance(exc, TtsOwnerConflict) else
                        'tts_ownership_unavailable' if isinstance(exc, TtsOwnershipUnavailable) else
                        'startup_not_idle' if isinstance(exc, StartupNotIdle) else
                        'backend_invalid_result' if isinstance(exc, WireError) else 'backend_failed')
                retryable = code in ('gpu_busy', 'tts_owner_conflict', 'tts_ownership_unavailable', 'startup_not_idle')
                status, response = 503 if retryable else 502, make_response(job.owner, error=code, retryable=retryable)
            with self.condition:
                if self.clock() >= job.deadline:
                    self._cancel_locked(job, 'deadline_exceeded')
                if not job.done.is_set():
                    job.status, job.response = status, response
                    job.done.set()
                    self.counts['completed' if status == 200 else 'failed'] += 1
                self._forget_locked(job)
                self.active = None
                self.condition.notify_all()

    def health(self):
        with self.condition:
            result = dict(protocol_version=1, ok=not self.closed, role='model_inference_only',
                active=self.active is not None, pending=len(self.pending),
                request_metadata=len(self.seen), owner_metadata=len(self.generations),
                limits=dict(max_pending=self.max_pending, max_seen=self.max_seen, max_owners=self.max_owners),
                counts=dict(self.counts), persistence='none', request_logging=False)
        if hasattr(self.backend, 'health'):
            result['backend'] = self.backend.health()
        return result

    def preflight(self, *, deadline):
        if not hasattr(self.backend, 'preflight'):
            return {'protocol_version': 1, 'ok': False, 'error': {'code': 'preflight_unavailable', 'retryable': False}}
        with self.condition:
            idle = self.active is None and not self.pending and not self.closed
        value = self.backend.preflight(deadline=deadline)
        value['scheduler_idle'] = idle
        if not idle:
            value['startup']['can_warm_unique_tts_now'] = False
            value['startup']['blocked_reasons'].append('scheduler_not_idle')
        return value

    def close(self):
        with self.condition:
            self.closed = True
            for job in tuple(self.jobs.values()):
                self._cancel_locked(job, 'service_closed')
            self._trim_pending_locked()
            self.condition.notify_all()
        if hasattr(self.backend, 'close'):
            self.backend.close()
        self.worker.join(timeout=1)


class _ColdGpuStartRequired(RuntimeError):
    """A child lifecycle race requires readmission with its original deadline."""


class TtsOwnerConflict(RuntimeError):
    pass


class TtsOwnershipUnavailable(RuntimeError):
    pass


class StartupNotIdle(RuntimeError):
    pass


class WindowsTtsProcessProbe:
    """Read only model worker ownership. Never sends a signal or reads a DB."""
    def __init__(self, *, run=subprocess.run):
        self.run = run

    def read(self, *, deadline, owned_pid=None):
        if os.name != 'nt':
            return {'available': False, 'error': 'unsupported_platform'}
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        command = r'''[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
@(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | ForEach-Object {
 [pscustomobject]@{pid=[int]$_.ProcessId;ppid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString('o');command=$_.CommandLine}
}) | ConvertTo-Json -Depth 3 -Compress'''
        try:
            result = self.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                capture_output=True, timeout=min(1.2, remaining),
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode or len(result.stdout) > 1024*1024:
                raise ValueError()
            raw = json.loads(result.stdout.decode('utf-8-sig'))
            rows = raw if isinstance(raw, list) else [raw]
            matches = {}
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get('command'), str):
                    continue
                args = [part.strip('"') for part in shlex.split(row['command'], posix=False)]
                if not any(Path(arg.replace('\\', '/')).name.lower() == 'omnivoice_voice.py' for arg in args):
                    continue
                if type(row.get('pid')) is not int or type(row.get('ppid')) is not int:
                    raise ValueError()
                matches[row['pid']] = dict(pid=row['pid'], ppid=row['ppid'],
                    created_utc=row.get('created_utc'), mode='ram' if '--memory-only' in args else 'cached')
            families = {}
            for token, row in matches.items():
                root, visited = token, set()
                while matches[root]['ppid'] in matches:
                    if root in visited:
                        raise ValueError()
                    visited.add(root)
                    root = matches[root]['ppid']
                families.setdefault(root, []).append(row)
            workers = [dict(root_pid=root, pids=sorted(row['pid'] for row in family),
                            modes=sorted({row['mode'] for row in family}),
                            owned=any(row['pid'] == owned_pid for row in family))
                       for root, family in families.items()]
            return dict(available=True, logical_workers=len(workers),
                        external_workers=sum(not row['owned'] for row in workers),
                        owned_workers=sum(row['owned'] for row in workers), workers=workers,
                        scope='read-only process metadata; launcher and interpreter children form one family')
        except (OSError, ValueError, subprocess.SubprocessError):
            return {'available': False, 'error': 'process_probe_unavailable'}


class _BudgetReader(io.RawIOBase):
    """HTTPResponse input with cancellable reads, including partial lines.

    Windows may leave an outstanding recv blocked after another thread calls
    shutdown. Poll a nonblocking owned socket rather than relying on that race
    or retrying a timed-out socket.makefile (which becomes unusable).
    """
    def __init__(self, connection, deadline, cancelled):
        super().__init__()
        self.connection, self.deadline, self.cancelled = connection, deadline, cancelled

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            LocalModelBackend._check(self.deadline, self.cancelled)
            readable, _, _ = select.select([self.connection], [], [],
                min(.025, max(.001, self.deadline-time.monotonic())))
            if readable:
                try:
                    return self.connection.recv_into(buffer)
                except BlockingIOError:
                    continue


class _ResponseSocket:
    def __init__(self, connection, deadline, cancelled):
        self.connection, self.deadline, self.cancelled = connection, deadline, cancelled

    def makefile(self, mode):
        if mode != 'rb':
            raise ValueError('Read-only backend response')
        return io.BufferedReader(_BudgetReader(self.connection, self.deadline, self.cancelled))


class LocalModelBackend:
    """Existing fixed 27B and OmniVoice16 with enforced GPU admission."""
    FIXED_MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'

    def __init__(self, model, ollama_host, voice_python, tts_model_path, gpu_coordinator, *, tts_process_probe=None):
        target = urlsplit(ollama_host)
        if (model != self.FIXED_MODEL or target.scheme != 'http'
                or target.hostname not in ('127.0.0.1', 'localhost')
                or target.path not in ('', '/') or target.query or target.fragment or target.username):
            raise ValueError('Require the configured fixed local 27B endpoint')
        if gpu_coordinator.policy.mode not in ('adaptive', 'serial'):
            raise ValueError('Candidate model host requires enforcing GPU admission')
        self.model, self.ollama_host, self.gpu = model, ollama_host, gpu_coordinator
        self.tts_process_probe = tts_process_probe or WindowsTtsProcessProbe()
        from tools.voice_worker_transport import BoundedSpeechProcess
        self.voice_python, self.tts_model_path = str(Path(voice_python).resolve()), str(Path(tts_model_path).resolve())
        self._gpu_start_state = threading.local()
        self._warm_process = None
        self.voice = BoundedSpeechProcess(self._voice_command, None, max_line=MAX_RESPONSE)

    def _voice_command(self):
        if getattr(self._gpu_start_state, 'allow_cold_start', False) is not True:
            raise _ColdGpuStartRequired()
        self._check_sole_tts_owner(deadline=self._gpu_start_state.deadline)
        if not Path(self.voice_python).is_file():
            raise RuntimeError('voice_runtime_unavailable')
        return [self.voice_python, '-B', '-s', '-u',
                str(AURA / 'board/runtime/audio/omnivoice_voice.py'), '--memory-only',
                '--model-path', self.tts_model_path]

    def _check_sole_tts_owner(self, *, deadline):
        value = self.tts_process_probe.read(deadline=deadline,
            owned_pid=self._owned_voice_pid())
        if value.get('available') is not True:
            raise TtsOwnershipUnavailable()
        if value.get('external_workers') != 0:
            raise TtsOwnerConflict()
        return value

    def _owned_voice_pid(self):
        process = self.voice.process
        # A retained PID from a dead process is not ownership evidence. Popen's
        # live handle prevents PID reuse while this owned process is alive.
        if process is not None and callable(getattr(process, 'poll', None)) and process.poll() is None:
            return process.pid
        return None

    @classmethod
    def from_config(cls, *, aura=AURA, voice_python=sys.executable, tts_model_path=None):
        aura = Path(aura)
        model = json.loads((aura / 'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
        from common.gpu_coordination import GpuCoordinator, GpuPolicy, NvidiaMemoryProbe, OllamaResidencyProbe
        policy = GpuPolicy.from_dict(json.loads((aura / 'config/gpu_runtime.local.json').read_text(encoding='utf-8')))
        gpu = GpuCoordinator(policy, NvidiaMemoryProbe(),
            llm_residency=OllamaResidencyProbe(model['ollama_host'], model['model']))
        return cls(model['model'], model['ollama_host'], voice_python,
                   tts_model_path or aura / 'models/tts/OmniVoice', gpu)

    @staticmethod
    def _check(deadline, cancelled):
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Require original finite deadline')
        if cancelled.is_set():
            raise InterruptedError()
        if time.monotonic() >= deadline:
            raise TimeoutError()

    def llm(self, payload, *, deadline, cancelled):
        with self.gpu.acquire('llm', deadline=deadline, cancelled=cancelled):
            self._check(deadline, cancelled)
            return self._ollama(payload, deadline=deadline, cancelled=cancelled)

    def preload_llm(self, *, deadline, cancelled):
        """Explicit no-prompt fixed-model load under original GPU admission.

        Ollama's empty /api/generate request loads the model only. Keep the
        same context size and keep-alive as normal project inference so the
        first conversation does not request a different runner allocation.
        No unload, model creation, template, persona or business text is sent.
        """
        with self.gpu.acquire('llm', deadline=deadline, cancelled=cancelled):
            self._check(deadline, cancelled)
            self._preload_llm_request(deadline=deadline, cancelled=cancelled)

    def _preload_llm_request(self, *, deadline, cancelled):
        body = dict(model=self.model, prompt='', stream=False, keep_alive=-1,
                    think=False, options={'num_ctx': 2048})
        target = urlsplit(self.ollama_host)
        conn = http.client.HTTPConnection('127.0.0.1', target.port or 80,
            timeout=max(.001, deadline-time.monotonic()))
        response = None
        try:
            self._check(deadline, cancelled)
            conn.connect()
            conn.sock.setblocking(False)
            encoded = json.dumps(body, ensure_ascii=False).encode('utf-8')
            header = ('POST /api/generate HTTP/1.1\r\nHost: 127.0.0.1:' + str(target.port or 80)
                      + '\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(encoded))
                      + '\r\nConnection: close\r\n\r\n').encode('ascii')
            outgoing = memoryview(header + encoded)
            while outgoing:
                self._check(deadline, cancelled)
                _, writable, _ = select.select([], [conn.sock], [],
                    min(.025, max(.001, deadline-time.monotonic())))
                if writable:
                    try:
                        sent = conn.sock.send(outgoing)
                    except BlockingIOError:
                        continue
                    if sent <= 0:
                        raise EOFError()
                    outgoing = outgoing[sent:]
            response = http.client.HTTPResponse(_ResponseSocket(conn.sock, deadline, cancelled))
            response.begin()
            raw = response.read(65537)
            self._check(deadline, cancelled)
            if response.status != 200 or len(raw) > 65536:
                raise RuntimeError('preload_invalid_response')
            value = json.loads(raw)
            if (not isinstance(value, dict) or value.get('model') != self.model
                    or value.get('done') is not True or value.get('error')
                    or value.get('response') != ''):
                raise RuntimeError('preload_invalid_result')
        except (OSError, EOFError, http.client.HTTPException):
            self._check(deadline, cancelled)
            raise RuntimeError('preload_backend_io') from None
        finally:
            if response is not None:
                response.close()
            conn.close()

    def _ollama(self, payload, *, deadline, cancelled):
        # Reuse the installed model's sampling/context settings, then replace
        # messages wholesale. Never call stream_body/build_system_prompt: those
        # construct business context/persona that only the board may own.
        from tools.dialogue_host_ollama import chat_body
        from common.inference_output_contract import build_body, StreamObservation
        body = build_body(chat_body(self.model, '', '', fast=True), payload)
        observation = (StreamObservation(time.monotonic())
                       if 'output_format' in payload['options'] else None)
        target = urlsplit(self.ollama_host)
        conn = http.client.HTTPConnection(target.hostname, target.port or 80,
                                         timeout=max(.001, deadline-time.monotonic()))
        response = None
        try:
            conn.connect()
            conn.sock.setblocking(False)
            encoded = json.dumps(body, ensure_ascii=False).encode('utf-8')
            header = ('POST /api/chat HTTP/1.1\r\nHost: ' + target.hostname + ':' + str(target.port or 80)
                      + '\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(encoded))
                      + '\r\nConnection: close\r\n\r\n').encode('ascii')
            outgoing = memoryview(header + encoded)
            while outgoing:
                self._check(deadline, cancelled)
                _, writable, _ = select.select([], [conn.sock], [],
                    min(.025, max(.001, deadline-time.monotonic())))
                if writable:
                    try:
                        sent = conn.sock.send(outgoing)
                    except BlockingIOError:
                        continue
                    if sent <= 0:
                        raise EOFError()
                    outgoing = outgoing[sent:]
            response = http.client.HTTPResponse(_ResponseSocket(conn.sock, deadline, cancelled))
            response.begin()
            if response.status != 200:
                raise RuntimeError('backend_http')
            chunks, size, packets, metrics = [], 0, 0, {}
            while True:
                self._check(deadline, cancelled)
                raw = response.readline(32769)
                self._check(deadline, cancelled)
                if not raw or len(raw) > 32768:
                    raise RuntimeError('backend_packet')
                packets += 1
                if packets > 16384:
                    raise RuntimeError('backend_packet_limit')
                packet = json.loads(raw)
                if not isinstance(packet, dict) or packet.get('error'):
                    raise RuntimeError('backend_failed')
                if observation is not None:
                    observation.packet(packet, time.monotonic())
                message = packet.get('message') or {}
                delta = message.get('content') or ''
                if not isinstance(delta, str):
                    raise RuntimeError('backend_packet')
                size += len(delta.encode('utf-8'))
                if size > MAX_OUTPUT_BYTES:
                    raise RuntimeError('backend_output_limit')
                if delta:
                    chunks.append(delta)
                if packet.get('done') is True:
                    for key in ('prompt_eval_count', 'eval_count'):
                        value = packet.get(key)
                        if type(value) is int and value >= 0:
                            metrics[key] = value
                    for key in ('load_duration', 'prompt_eval_duration', 'eval_duration', 'total_duration'):
                        value = packet.get(key)
                        if type(value) in (int, float) and math.isfinite(value) and value >= 0:
                            metrics[key + '_ms'] = round(value / 1e6, 2)
                    if observation is not None:
                        metrics.update(observation.finish(packet))
                    return {'text': ''.join(chunks), 'metrics': metrics}
        except (OSError, EOFError, http.client.HTTPException):
            self._check(deadline, cancelled)
            raise RuntimeError('backend_io') from None
        finally:
            if response is not None:
                response.close()
            conn.close()

    def tts(self, payload, *, deadline, cancelled):
        result = self._voice_request({'text': payload['text']}, deadline=deadline,
                                     cancelled=cancelled, request_id=payload['request_id'])
        return {'audio': result['audio']}

    def _tts_ready(self):
        status = self.voice.health()
        return bool(status['alive'] and not status['quarantined'] and not status['closed']
                    and self._warm_process is not None and self.voice.process is self._warm_process)

    def _voice_request(self, request, *, deadline, cancelled, request_id, warmup=False):
        admission_deadline = min(deadline, time.monotonic() + self.gpu.policy.max_wait_seconds)
        force_cold = False
        for attempt in range(2):
            status = self.voice.health()
            cold = bool(warmup or force_cold or not status['alive'] or status['quarantined']
                        or self._warm_process is None or self.voice.process is not self._warm_process)
            with self.gpu.acquire('tts', deadline=deadline, cancelled=cancelled,
                                  cold=cold, wait_deadline=admission_deadline):
                self._gpu_start_state.allow_cold_start = cold
                self._gpu_start_state.deadline = deadline
                try:
                    self._check(deadline, cancelled)
                    # Once started, drain within the ORIGINAL deadline. Early
                    # return would retire the warm worker/release its GPU lease.
                    result = self.voice.request(request, deadline=deadline, request_id=request_id)
                    if warmup and result.get('ready') is not True:
                        raise RuntimeError('warmup_not_ready')
                    if not warmup:
                        decode_audio(result.get('audio'))
                    self.gpu.note_tts(result, warmup=warmup, cold=cold)
                    self._warm_process = self.voice.process
                    self._check(deadline, cancelled)
                    return result
                except _ColdGpuStartRequired:
                    if not cold and attempt == 0:
                        force_cold = True
                        continue
                    raise
                except InterruptedError:
                    # A drained cancelled synthesis still leaves the SAME
                    # proven warm process; do not force a model reload.
                    raise
                except Exception:
                    self._warm_process = None
                    raise
                finally:
                    self._gpu_start_state.allow_cold_start = False
                    self._gpu_start_state.deadline = None

    def warmup_tts(self, *, deadline, cancelled, request_id):
        """Explicit startup only; never called by construction or /health.

        The external switch owner must first release its old TTS owner and
        arrange an idle window. This method verifies metadata, not authority to
        stop a process or to move any business writer. No model is unloaded.
        """
        self._check(deadline, cancelled)
        self._check_sole_tts_owner(deadline=deadline)
        with self.gpu.condition:
            if self.gpu.active or self.gpu.pending:
                raise StartupNotIdle()
        if self.voice.active_id is not None:
            raise StartupNotIdle()
        residency = self.gpu.llm_residency.status(deadline=deadline, refresh=True)
        if residency.get('available') is not True or residency.get('llm_resident') is not False:
            raise StartupNotIdle()
        self._voice_request({'type': 'warmup'}, deadline=deadline, cancelled=cancelled,
                            request_id=request_id, warmup=True)
        self._check(deadline, cancelled)
        if not self._tts_ready():
            raise RuntimeError('warmup_worker_not_ready')
        return {'target': 'tts', 'ready': True, 'num_step': 16, 'memory_only': True}

    def warmup(self, payload, *, deadline, cancelled):
        return self.warmup_tts(deadline=deadline, cancelled=cancelled,
                               request_id=payload['request_id'])

    def preflight(self, *, deadline):
        """Read-only capacity snapshot. It never reserves memory or starts work."""
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Require preflight deadline')
        now = time.monotonic()
        if deadline <= now:
            raise TimeoutError()
        p = self.gpu.policy
        ownership = self.tts_process_probe.read(deadline=deadline,
            owned_pid=self._owned_voice_pid())
        residency = self.gpu.llm_residency.status(deadline=deadline, refresh=True)
        try:
            sample = self.gpu.probe.read(timeout=max(.001, min(.4, deadline-time.monotonic())))
            memory = sample.public(time.monotonic())
            memory_valid = (sample.gpu_uuid == p.gpu_uuid
                and 0 <= time.monotonic()-sample.observed_at <= p.sample_max_age_seconds)
        except Exception:
            memory, memory_valid = {'available': False}, False
        with self.gpu.condition:
            active = list(self.gpu.active.values())
            pending = len(self.gpu.pending)
        reserved = sum((p.llm_extra_mib if self.gpu._fresh_resident(residency,
            after=row['admitted_at'], after_sequence=row['observation_sequence']) else p.llm_cold_extra_mib)
            if row['kind'] == 'llm' else row['extra_mib'] for row in active)
        ready = self._tts_ready()
        free = memory.get('free_mib') if memory_valid else None
        admission = {}
        for kind, extra in (('llm', self.gpu._llm_extra(residency)),
                            ('tts', p.tts_extra_mib if ready else p.tts_cold_extra_mib)):
            required = p.reserve_mib + extra + reserved
            reason = ('memory_unavailable_or_unverified' if free is None else
                      'same_phase_active' if any(row['kind'] == kind for row in active) else
                      'serialized_peak' if p.mode == 'serial' and active else
                      'insufficient_headroom' if free < required else 'snapshot_headroom_available')
            admission[kind] = dict(extra_mib=extra, reserve_mib=p.reserve_mib,
                active_reserved_mib=reserved, required_free_mib=required, observed_free_mib=free,
                shortfall_mib=max(0, required-free) if free is not None else None,
                can_admit_now=reason == 'snapshot_headroom_available', reason=reason,
                phase='warm' if kind == 'tts' and ready or kind == 'llm' and extra == p.llm_extra_mib else 'cold_or_unknown')
        blocked = []
        if ownership.get('available') is not True:
            blocked.append('tts_ownership_unavailable')
        elif ownership.get('external_workers') != 0:
            blocked.append('external_tts_owner_present')
        if active or pending or self.voice.active_id is not None:
            blocked.append('model_executor_not_idle')
        if residency.get('available') is not True:
            blocked.append('llm_residency_unavailable')
        elif residency.get('llm_resident') is not False:
            blocked.append('llm_already_resident_for_tts_first_startup')
        # Warmup itself always reserves the calibrated COLD budget, even if an
        # earlier explicit warmup already made this process ready.
        warm_required = p.reserve_mib+p.tts_cold_extra_mib+reserved
        if free is None or free < warm_required:
            blocked.append('cold_tts_headroom_unavailable')
        return dict(protocol_version=1, ok=True, observation_only=True, reservation=False,
            gpu_policy=dict(mode=p.mode, enforcing=p.mode != 'observe', calibration_id=p.calibration_id),
            memory=memory, llm_residency=residency, tts_ownership=ownership,
            tts_ready=ready, admission=admission,
            startup=dict(can_warm_unique_tts_now=not blocked, blocked_reasons=blocked,
                order=['externally_release_old_tts_owner', 'explicit_ram_tts_warmup',
                       'verify_same_owned_worker_ready', 'recheck_original_llm_admission',
                       'load_existing_27b', 'recheck_steady_tts_admission'],
                cold_tts_required_free_mib=warm_required,
                post_warmup_llm_admission_must_be_rechecked=True,
                external_business_single_writer_confirmation_required=True,
                external_idle_and_process_ownership_confirmation_required=True,
                external_rollback_plan_required=True, automatic_stop_or_unload=False))

    def health(self):
        return dict(model=self.model, tts='omnivoice', num_step=16,
                    format_contract_version=1, output_formats=['json', 'dialogue_schema_v1', 'dialogue_abc_v1', 'dialogue_ab_v1'],
                    voice=self.voice.health(), tts_ready=self._tts_ready(),
                    warmup_automatic=False, gpu_coordination=self.gpu.public())

    def close(self):
        self.voice.close()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    INPUT_TIMEOUT = 5.

    def setup(self):
        super().setup()
        self.rfile.close()
        self.input_budget = _BudgetReader(self.connection, time.monotonic()+self.INPUT_TIMEOUT,
                                         threading.Event())
        self.rfile = io.BufferedReader(self.input_budget)

    def log_message(self, *args):
        pass

    def handle_one_request(self):
        self.input_budget.deadline = time.monotonic()+self.INPUT_TIMEOUT
        super().handle_one_request()

    def _json(self, status, body):
        encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if len(encoded) > MAX_RESPONSE:
            status, encoded = 502, b'{"ok":false,"error":{"code":"response_limit","retryable":false}}'
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(encoded)
        except (OSError, ValueError):
            pass

    def _error(self, status, code):
        self._json(status, {'protocol_version': 1, 'ok': False,
                           'error': {'code': code, 'retryable': False}})

    def _peer(self):
        return self.client_address[0] in self.server.allowed_peers

    def do_GET(self):
        if self.path == '/health' and self.client_address[0] in self.server.health_peers:
            return self._json(200, self.server.models.health())
        if not self._peer():
            return self._error(403, 'peer_denied')
        if self.path == '/v1/inference/preflight':
            try:
                value = self.server.models.preflight(deadline=time.monotonic()+2.)
                return self._json(200 if value.get('ok') else 503, value)
            except Exception:
                return self._error(503, 'preflight_unavailable')
        return self._error(404, 'unknown_path')

    def do_POST(self):
        received_at = self.server.models.clock()
        self.connection.settimeout(5)
        if not self._peer():
            return self._error(403, 'peer_denied')
        paths = {f'/v1/inference/{kind}': kind for kind in ('llm', 'tts', 'cancel', 'warmup')}
        if self.path not in paths:
            return self._error(404, 'unknown_path')
        if self.headers.get_content_type() != 'application/json':
            return self._error(415, 'content_type')
        lengths = self.headers.get_all('Content-Length') or []
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1:
            return self._error(411, 'content_length')
        try:
            if not lengths[0].isascii() or not lengths[0].isdigit():
                raise ValueError()
            length = int(lengths[0])
            if not 1 <= length <= MAX_BODY:
                return self._error(413, 'body_limit')
        except (ValueError, OverflowError):
            return self._error(400, 'content_length')
        self.input_budget.deadline = time.monotonic()+self.INPUT_TIMEOUT
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                return self._error(400, 'incomplete_body')
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError()
                    value[key] = item
                return value
            payload = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError, OSError, RecursionError):
            return self._error(400, 'invalid_json')
        # socket writes also have a finite bound; generation ownership remains
        # enforced even if the board disconnects before consuming the response.
        status, body = self.server.models.handle(paths[self.path], payload, received_at=received_at)
        self._json(status, body)

    def send_error(self, code, message=None, explain=None):
        self._error(code, 'http_error')


class InferenceServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, address, models, *, allowed_peers, health_peers=None):
        self.models, self.allowed_peers = models, frozenset(allowed_peers)
        self.health_peers = self.allowed_peers if health_peers is None else frozenset(health_peers)
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, _Handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # Base implementation prints tracebacks, potentially including input.
        pass


def make_server(address, models, *, allowed_peers=None, local_health=False):
    host, _ = address
    if host not in ('127.0.0.1', '192.168.50.1'):
        raise ValueError('Bind only loopback or the dedicated board Ethernet interface')
    peers = ('127.0.0.1',) if host == '127.0.0.1' else ('192.168.50.2',)
    if allowed_peers is not None:
        peers = tuple(allowed_peers)
        if not peers or set(peers) - {'127.0.0.1', '192.168.50.2'}:
            raise ValueError('Invalid board peer allowlist')
    if type(local_health) is not bool:
        raise ValueError('Local health access must be explicitly enabled')
    readers = set(peers)
    if local_health:
        readers.update(('127.0.0.1', host))
    return InferenceServer(address, models, allowed_peers=peers, health_peers=readers)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=('127.0.0.1', '192.168.50.1'), default='192.168.50.1')
    parser.add_argument('--port', type=int, default=8797)
    parser.add_argument('--voice-python', default=sys.executable)
    parser.add_argument('--tts-model-path', type=Path, default=AURA / 'models/tts/OmniVoice')
    parser.add_argument('--runtime-root', type=Path, required=True,
        help='Existing legacy model_host root; shares its voice8792.instance.lock, opens no DB')
    parser.add_argument('--manual-startup', action='store_true',
        help='Isolated debugging only: serve explicit warmup API without automatic startup sequence')
    parser.add_argument('--local-health', action='store_true',
        help='Allow this host to read GET /health metadata for the runtime dashboard')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('Invalid port')
    if not args.runtime_root.is_dir():
        parser.error('Use the existing legacy model_host runtime directory')
    from tools.service_instance_lock import ServiceInstanceLock
    from tools.voice_startup_guard import cold_capacity_preflight
    from tools.model_inference_startup import startup_models
    deadline = time.monotonic()+300.
    with ServiceInstanceLock(args.runtime_root / 'voice8792.instance.lock') as lock:
        # Inspects the actual fixed project daemon, calibrated fit/environment,
        # D-drive model storage and legacy ownership before constructing a TTS.
        startup_evidence = cold_capacity_preflight(AURA, args.runtime_root, lock=lock,
            listen=args.host, port=8792, deadline=deadline)
        backend = LocalModelBackend.from_config(voice_python=args.voice_python,
                                                tts_model_path=args.tts_model_path)
        models = server = None
        try:
            if not args.manual_startup:
                startup_evidence = startup_models(backend, lock=lock, deadline=deadline)
            if time.monotonic() >= deadline:
                raise TimeoutError('Original model-only startup deadline expired')
            models = InferenceHost(backend)
            server = make_server((args.host, args.port), models, local_health=args.local_health)
            print(json.dumps({'status': 'READY', 'role': 'model_inference_only',
                'listen': args.host, 'port': args.port,
                'startup': startup_evidence, 'manual_startup': args.manual_startup}), flush=True)
            server.serve_forever(poll_interval=.2)
        finally:
            if server is not None:
                server.server_close()
            if models is not None:
                models.close()
            else:
                backend.close()


if __name__ == '__main__':
    main()
