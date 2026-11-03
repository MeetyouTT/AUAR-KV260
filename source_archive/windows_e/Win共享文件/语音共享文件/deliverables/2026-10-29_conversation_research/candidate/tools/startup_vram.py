"""Optional, calibrated cold-TTS startup preparation; never called per turn.

No imports or constructors load a model, allocate CUDA, or issue a request.
Only prepare_cold_tts_startup may send the narrowly scoped unload request.
Call it before constructing ModelHost, while holding the service lifetime lock.
"""
from dataclasses import dataclass
import http.client
import json
import math
import ntpath
import socket
import threading
import time

if __package__:
    from .service_instance_lock import ServiceInstanceLock
else:
    from service_instance_lock import ServiceInstanceLock

PROJECT_HOST = 'http://127.0.0.1:11435'
PROJECT_MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
PROJECT_MODELS_DIRECTORY = r'D:\AIModels\Ollama-AURA'
MAX_RESPONSE = 1024 * 1024


class StartupVramError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectOllamaOwner:
    """Evidence supplied by the parent's fresh, bounded ownership inspection.

    HTTP /api/ps does not establish no_inflight. The caller must establish it
    from its startup ownership/coordination, not infer it from an empty list.
    created is the daemon's stable process creation identifier, not probe time.
    """
    pid: int
    created: str
    executable: str
    host: str
    models_directory: str
    no_inflight: bool


def _remaining(deadline, clock):
    value = deadline - clock()
    if value <= 0:
        raise TimeoutError('Original cold-TTS startup deadline expired')
    return value


class FixedProjectOllamaApi:
    """Only 127.0.0.1:11435, bounded JSON, one absolute deadline per call."""
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock

    def _request(self, method, path, body, *, deadline):
        if (method, path) not in {('GET', '/api/ps'), ('POST', '/api/generate')}:
            raise ValueError('Startup helper route is not allowed')
        payload = None if body is None else json.dumps(body, separators=(',', ':')).encode('utf-8')
        connection = http.client.HTTPConnection('127.0.0.1', 11435, timeout=_remaining(deadline, self.clock))
        timer = None
        try:
            connection.connect()
            active_socket = connection.sock
            def stop_socket():
                try:
                    active_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            # Covers headers and the entire body, including a slow trickle.
            timer = threading.Timer(_remaining(deadline, self.clock), stop_socket)
            timer.daemon = True
            timer.start()
            connection.request(method, path, payload, {'Content-Type': 'application/json', 'Connection': 'close'})
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE + 1)
            _remaining(deadline, self.clock)
            if response.status != 200 or len(raw) > MAX_RESPONSE:
                raise StartupVramError('Project Ollama rejected the bounded startup request')
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise StartupVramError('Invalid project Ollama startup JSON')
            return value
        finally:
            if timer is not None:
                timer.cancel()
            connection.close()

    def ps(self, *, deadline):
        value = self._request('GET', '/api/ps', None, deadline=deadline)
        rows = value.get('models')
        if not isinstance(rows, list) or len(rows) > 16:
            raise StartupVramError('Invalid project Ollama residency list')
        return rows

    def unload(self, model, *, deadline):
        if model != PROJECT_MODEL:
            raise StartupVramError('Only the pinned project model may be unloaded')
        return self._request('POST', '/api/generate',
            {'model': PROJECT_MODEL, 'keep_alive': 0, 'stream': False}, deadline=deadline)


def _owner_matches(actual, expected):
    if (not isinstance(actual, ProjectOllamaOwner) or type(actual.pid) is not int or actual.pid <= 0
            or any(not isinstance(value, str) or not value for value in
                (actual.created, actual.executable, actual.models_directory))):
        return False
    return (actual.pid == expected.pid and actual.created == expected.created
        and ntpath.normcase(ntpath.normpath(actual.executable)) == ntpath.normcase(ntpath.normpath(expected.executable))
        and actual.host == expected.host == PROJECT_HOST
        and ntpath.normcase(ntpath.normpath(actual.models_directory))
            == ntpath.normcase(ntpath.normpath(expected.models_directory))
            == ntpath.normcase(PROJECT_MODELS_DIRECTORY)
        and actual.no_inflight is True)


def _only_project(rows):
    if not isinstance(rows, list) or len(rows) > 16:
        raise StartupVramError('Invalid project Ollama residency list')
    for row in rows:
        if (not isinstance(row, dict) or row.get('name') != PROJECT_MODEL
                or row.get('model', PROJECT_MODEL) != PROJECT_MODEL):
            raise StartupVramError('Another or ambiguous model is present on project 11435; leave it untouched')
    return rows


def prepare_cold_tts_startup(config, policy, *, lock, deadline, expected_owner,
        verify_owner, voice_is_listening, memory_sample, api=None,
        clock=time.monotonic, wait=time.sleep):
    """Reserve startup order, not physical VRAM; no regular-turn unloading.

    policy is the already validated GPU-policy dict. All three callbacks take
    the same absolute deadline and MUST bound their own lock/I/O waits to it:
      verify_owner(deadline) -> fresh ProjectOllamaOwner
      voice_is_listening(deadline) -> literal bool for actual port 8792
      memory_sample(deadline) -> gpu_uuid/free_mib/observed_at attributes
    They must not load, unload, record, play, or stop anything.
    """
    if (not isinstance(config, dict) or config.get('ollama_host') != PROJECT_HOST
            or config.get('model') != PROJECT_MODEL):
        raise StartupVramError('Startup config does not match the pinned project host/model')
    if not isinstance(policy, dict) or policy.get('mode', 'observe') not in ('observe', 'adaptive', 'serial'):
        raise StartupVramError('Invalid startup GPU policy')
    if not isinstance(lock, ServiceInstanceLock) or not lock.held:
        raise StartupVramError('Hold the service lifetime lock before startup preparation')
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Startup preparation requires the original finite deadline')
    _remaining(deadline, clock)
    if policy.get('mode', 'observe') == 'observe':
        return {'status': 'skipped_observe', 'unloaded': False, 'capacity_verified': False}
    cold, reserve = policy.get('tts_cold_extra_mib', 0), policy.get('reserve_mib', 0)
    identity = policy.get('gpu_uuid', '')
    if (not policy.get('calibration_id') or not identity or type(cold) is not int or cold <= 0
            or type(reserve) is not int or reserve < 128):
        return {'status': 'skipped_uncalibrated', 'unloaded': False, 'capacity_verified': False}
    if cold > 65536 or reserve > 65536 or not isinstance(identity, str):
        raise StartupVramError('Invalid measured cold-TTS budget')
    if (not isinstance(expected_owner, ProjectOllamaOwner) or type(expected_owner.pid) is not int
            or expected_owner.pid <= 0 or not isinstance(expected_owner.created, str) or not expected_owner.created
            or not isinstance(expected_owner.executable, str) or not expected_owner.executable
            or not _owner_matches(expected_owner, expected_owner)):
        raise StartupVramError('A verified quiescent project Ollama owner is required')
    required = cold + reserve
    api = api or FixedProjectOllamaApi(clock=clock)

    def guard():
        _remaining(deadline, clock)
        if not lock.held:
            raise StartupVramError('Startup lifetime lock was released')
        actual = verify_owner(deadline)
        _remaining(deadline, clock)
        if not _owner_matches(actual, expected_owner):
            raise StartupVramError('Project Ollama owner changed or is not quiescent')
        listening = voice_is_listening(deadline)
        _remaining(deadline, clock)
        if type(listening) is not bool or listening:
            raise StartupVramError('Voice 8792 is active or its absence could not be established')

    def memory():
        sample = memory_sample(deadline)
        _remaining(deadline, clock)
        free, observed = getattr(sample, 'free_mib', None), getattr(sample, 'observed_at', None)
        if (getattr(sample, 'gpu_uuid', None) != identity or type(free) is not int or free < 0
                or type(observed) not in (int, float) or not math.isfinite(observed)
                or not 0 <= clock() - observed <= .75):
            raise StartupVramError('Fresh calibrated GPU free memory is unavailable')
        return free

    guard()
    rows = _only_project(api.ps(deadline=deadline))
    _remaining(deadline, clock)
    before = memory()
    if before >= required:
        return {'status': 'sufficient', 'unloaded': False, 'capacity_verified': True,
            'required_free_mib': required, 'before_free_mib': before, 'after_free_mib': before}
    if not rows:
        raise StartupVramError('Cold-TTS memory is insufficient and no owned project cache can be released')
    # Recheck both ownership and model set immediately before the only mutation.
    guard()
    rows = _only_project(api.ps(deadline=deadline))
    _remaining(deadline, clock)
    if not rows:
        # Natural expiry raced with the first snapshot: only await recovery.
        unloaded = False
    else:
        # Do not discard the project cache if global free memory recovered
        # during ownership/residency checks; this may happen independently.
        current_free = memory()
        if current_free >= required:
            return {'status': 'sufficient', 'unloaded': False, 'capacity_verified': True,
                'required_free_mib': required, 'before_free_mib': before, 'after_free_mib': current_free}
        guard()
        result = api.unload(PROJECT_MODEL, deadline=deadline)
        _remaining(deadline, clock)
        if (not isinstance(result, dict) or result.get('done') is not True
                or result.get('done_reason') != 'unload' or result.get('model') != PROJECT_MODEL
                or result.get('response') != ''):
            raise StartupVramError('Project model unload was not explicitly acknowledged')
        unloaded = True
    while True:
        guard()
        rows = _only_project(api.ps(deadline=deadline))
        _remaining(deadline, clock)
        free = memory()
        if not rows and free >= required:
            return {'status': 'released_project_cache' if unloaded else 'naturally_released',
                'unloaded': unloaded, 'capacity_verified': True, 'required_free_mib': required,
                'before_free_mib': before, 'after_free_mib': free}
        wait(min(.05, _remaining(deadline, clock)))
