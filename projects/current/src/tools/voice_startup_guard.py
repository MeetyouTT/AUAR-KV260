"""Read-only cold capacity preflight under the voice process lifetime lock.

Never unloads, starts, stops, records or plays anything. An absent voice port
or an empty Ollama residency list never proves that no request is in flight.
"""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import http.client
import json
import math
import ntpath
from pathlib import Path
import re
import socket
import subprocess
import threading
import time

if __package__:
    from .service_instance_lock import ServiceInstanceLock
else:
    from service_instance_lock import ServiceInstanceLock

HOST = 'http://127.0.0.1:11435'
MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
MODEL_DIRECTORY = r'D:\AIModels\Ollama-AURA'


class StartupGuardError(RuntimeError):
    pass


class ColdStartupCapacityError(StartupGuardError):
    def __init__(self, evidence):
        self.evidence = evidence
        cold = evidence['cold_sample']
        super().__init__('Cold TTS needs %s MiB free (%s cold + %s reserve), available %s MiB. '
            'No quiescent handoff was proven; automatic unloading is disabled. '
            'Use the controlled owned-service reload path.' %
            (cold['required_free_mib'], cold['tts_cold_extra_mib'], cold['reserve_mib'], cold['free_mib']))


def _remaining(deadline, clock):
    value = deadline - clock()
    if value <= 0:
        raise TimeoutError('Original 300-second voice startup budget expired')
    return value


def _path(value):
    return ntpath.normcase(ntpath.normpath(value)) if isinstance(value, str) and value else ''


class ReadOnlyStartupChecks:
    """Bounded installed-project checks; construction performs no I/O."""
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock

    def _powershell_json(self, command, deadline):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            capture_output=True, timeout=min(15., _remaining(deadline, self.clock)),
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        _remaining(deadline, self.clock)
        if result.returncode or len(result.stdout) > 262144:
            raise StartupGuardError('Cannot establish actual local listener ownership')
        return json.loads(result.stdout.decode('utf-8-sig'))

    def voice_is_listening(self, deadline):
        command = r"""[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference='Stop'
$voiceListeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -eq 8792 })
ConvertTo-Json -InputObject $voiceListeners -Depth 3 -Compress
"""
        value = self._powershell_json(command, deadline)
        if not isinstance(value, list):
            raise StartupGuardError('Invalid voice listener inspection')
        return bool(value)

    def ownership(self, deadline):
        # Same fixed read-only scope as installed project_ollama.inspect_ownership,
        # with the subprocess bounded by the caller's remaining deadline.
        command = r"""[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$ownerListeners=@(Get-NetTCPConnection -State Listen -LocalPort 11435 -ErrorAction SilentlyContinue)
$ownerIds=@($ownerListeners.OwningProcess | Select-Object -Unique)
if ($ownerIds.Count -ne 1) { throw 'Project listener owner is not unique' }
$ownerProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$ownerIds[0])
if (-not $ownerProcess) { throw 'Project listener process disappeared' }
[pscustomobject]@{pid=[int]$ownerProcess.ProcessId;creation_utc=$ownerProcess.CreationDate.ToUniversalTime().ToString('o');
executable=$ownerProcess.ExecutablePath;command_line=$ownerProcess.CommandLine;parent_pid=[int]$ownerProcess.ParentProcessId;
listeners=@($ownerListeners | Select-Object LocalAddress,LocalPort,OwningProcess)} | ConvertTo-Json -Depth 5 -Compress
"""
        return self._powershell_json(command, deadline)

    def ollama_json(self, path, deadline):
        if path not in ('/api/version', '/api/ps'):
            raise StartupGuardError('Only read-only fixed Ollama routes are permitted')
        until = min(deadline, self.clock() + 2.)
        connection = http.client.HTTPConnection('127.0.0.1', 11435, timeout=_remaining(until, self.clock))
        timer = None
        try:
            connection.connect()
            active_socket = connection.sock
            def expire():
                try: active_socket.shutdown(socket.SHUT_RDWR)
                except OSError: pass
            timer = threading.Timer(_remaining(until, self.clock), expire)
            timer.daemon = True; timer.start()
            connection.request('GET', path, headers={'Connection': 'close'})
            response = connection.getresponse(); raw = response.read(1048577)
            _remaining(until, self.clock)
            if response.status != 200 or len(raw) > 1048576:
                raise StartupGuardError('Project Ollama read-only response was rejected')
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise StartupGuardError('Invalid project Ollama read-only JSON')
            return value
        finally:
            if timer is not None: timer.cancel()
            connection.close()

    def validate_gpu_policy(self, values):
        from common.gpu_coordination import GpuPolicy
        return asdict(GpuPolicy.from_dict(values))

    def executable_sha256(self, filename, deadline):
        result = hashlib.sha256()
        with Path(filename).open('rb') as source:
            while True:
                _remaining(deadline, self.clock)
                data = source.read(131072)
                if not data: break
                result.update(data)
        _remaining(deadline, self.clock)
        return result.hexdigest()

    def memory_sample(self, deadline):
        from common.gpu_coordination import NvidiaMemoryProbe
        probe = NvidiaMemoryProbe(clock=self.clock)
        return probe.read(timeout=min(.4, _remaining(deadline, self.clock)))


def _json_file(path, deadline, clock, *, limit=262144):
    _remaining(deadline, clock)
    with Path(path).open('rb') as source: raw = source.read(limit + 1)
    _remaining(deadline, clock)
    if len(raw) > limit:
        raise StartupGuardError('Startup configuration exceeds its read bound')
    value = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(value, dict):
        raise StartupGuardError('Invalid startup configuration object')
    return value, hashlib.sha256(raw).hexdigest()


def _validate_owner(value):
    if (not isinstance(value, dict) or type(value.get('pid')) is not int or value['pid'] <= 0
            or any(not isinstance(value.get(k), str) or not value[k]
                for k in ('creation_utc', 'executable', 'command_line'))
            or not re.search(r'(?:^|\s)serve\s*$', value['command_line'])):
        raise StartupGuardError('Incomplete actual project Ollama owner')
    rows = value.get('listeners')
    if (not isinstance(rows, list) or not rows or any(not isinstance(row, dict)
            or row.get('LocalPort') != 11435 or row.get('OwningProcess') != value['pid']
            or row.get('LocalAddress') != '127.0.0.1' for row in rows)):
        raise StartupGuardError('Actual project listener is not exclusive 127.0.0.1:11435')
    return value


def cold_capacity_preflight(aura, runtime_root, *, lock, host=HOST, model=MODEL,
        listen='192.168.50.1', port=8792, deadline, checks=None, clock=time.monotonic):
    """Read-only; fail promptly on insufficient cold capacity, never await idle."""
    if not isinstance(lock, ServiceInstanceLock) or not lock.held:
        raise StartupGuardError('Voice startup requires its held process lifetime lock')
    if lock.path.resolve() != (Path(runtime_root) / 'voice8792.instance.lock').resolve():
        raise StartupGuardError('Use the stable voice8792 lifetime lock in the configured runtime root')
    if (host != HOST or model != MODEL or port != 8792 or type(port) is not int
            or listen not in ('192.168.50.1', '127.0.0.1')):
        raise StartupGuardError('Startup guard is limited to the fixed project voice/Ollama endpoints')
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise StartupGuardError('Pass the original finite startup deadline')
    if _remaining(deadline, clock) > 300.001:
        raise StartupGuardError('Startup budget may not exceed the original 300 seconds')
    aura = Path(aura); checks = checks or ReadOnlyStartupChecks(clock=clock)
    paths = {
        'model': aura / 'config/board_dialogue_model.json',
        'storage': aura / 'config/model_storage.local.json',
        'gpu': aura / 'config/gpu_runtime.local.json',
    }
    values, snapshots = {}, {}
    for name, path in paths.items(): values[name], snapshots[name] = _json_file(path, deadline, clock)
    if values['model'] != {'model': model, 'ollama_host': host} or _path(values['storage'].get('ollama_directory')) != _path(MODEL_DIRECTORY):
        raise StartupGuardError('Configured project model/host/D-model storage differs')
    try: policy = checks.validate_gpu_policy(values['gpu'])
    except (ValueError, TypeError) as exc:
        raise StartupGuardError('GPU policy is not valid for this installed source: ' + str(exc)) from None
    _remaining(deadline, clock)
    if checks.voice_is_listening(deadline) is not False:
        raise StartupGuardError('Voice 8792 already listens or its absence is unknown')
    _remaining(deadline, clock)
    evidence = {'version': 1, 'mode': policy.get('mode', 'observe'),
        'capacity_verified': False, 'automatic_unload': False, 'no_inflight_proven': False,
        'gpu': {'available': False, 'reason': 'not_measured'}, 'cold_sample': {},
        'extra': {'project_owner_verified': False, 'controlled_reload_required': False}}
    cold, reserve = policy.get('tts_cold_extra_mib', 0), policy.get('reserve_mib', 0)
    if policy.get('mode', 'observe') == 'observe':
        return dict(evidence, status='skipped_observe')
    if (not policy.get('calibration_id') or not policy.get('gpu_uuid') or type(cold) is not int
            or cold <= 0 or type(reserve) is not int or reserve < 128):
        return dict(evidence, status='skipped_uncalibrated')
    paths['runtime'] = aura / 'config/ollama_runtime.local.json'
    paths['record'] = aura.parent / 'deliverables/2026-10-18_board_dialogue/project_ollama_process.json'
    for name in ('runtime', 'record'): values[name], snapshots[name] = _json_file(paths[name], deadline, clock)
    runtime, record = values['runtime'], values['record']
    required = {'schema_version', 'fit_target_mib', 'calibration_id', 'gpu_uuid', 'ollama_version'}
    if (set(runtime) != required or type(runtime['schema_version']) is not int or runtime['schema_version'] != 1
            or type(runtime['fit_target_mib']) is not int or not 1 <= runtime['fit_target_mib'] <= 1048576
            or not isinstance(runtime['calibration_id'], str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}', runtime['calibration_id'])
            or runtime['gpu_uuid'] != policy['gpu_uuid'] or not isinstance(runtime['ollama_version'], str)
            or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+.][\w.-]+)?', runtime['ollama_version'])):
        raise StartupGuardError('Ollama runtime policy differs from measured GPU binding')
    if (record.get('ready') is not True or record.get('host') != HOST
            or _path(record.get('models')) != _path(MODEL_DIRECTORY)
            or record.get('launch_environment_applied') is not True
            or record.get('runtime_policy') != dict(runtime, config_sha256=snapshots['runtime'])):
        raise StartupGuardError('Runtime policy was not recorded for the actual project daemon')
    current = _validate_owner(checks.ownership(deadline)); _remaining(deadline, clock)
    expected = _validate_owner(record.get('ownership'))
    owner_keys = ('pid', 'creation_utc', 'executable', 'command_line', 'listeners')
    if record.get('pid') != current['pid'] or any(expected[k] != current[k] for k in owner_keys):
        raise StartupGuardError('Actual daemon PID/creation/exe/command/listeners differ from owned process record')
    binding = record.get('bindings')
    if (not isinstance(binding, dict) or set(binding) != {'ollama_version', 'gpu_uuid', 'gpu_total_mib', 'executable', 'executable_sha256'}
            or binding['ollama_version'] != runtime['ollama_version'] or binding['gpu_uuid'] != policy['gpu_uuid']
            or _path(binding['executable']) != _path(current['executable'])
            or type(binding['gpu_total_mib']) is not int or not 0 < runtime['fit_target_mib'] < binding['gpu_total_mib']
            or not isinstance(binding['executable_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', binding['executable_sha256'])):
        raise StartupGuardError('Recorded executable/version/GPU bindings differ')
    if checks.executable_sha256(current['executable'], deadline) != binding['executable_sha256']:
        raise StartupGuardError('Installed project Ollama executable differs from recorded calibration')
    if checks.ollama_json('/api/version', deadline).get('version') != runtime['ollama_version']:
        raise StartupGuardError('Actual project Ollama version differs from runtime policy')
    rows = checks.ollama_json('/api/ps', deadline).get('models')
    if (not isinstance(rows, list) or len(rows) > 16 or any(not isinstance(row, dict)
            or row.get('name') != model or row.get('model', model) != model for row in rows)):
        raise StartupGuardError('Another or ambiguous model is resident in project 11435; leave it untouched')
    again = _validate_owner(checks.ownership(deadline))
    if any(again[k] != current[k] for k in owner_keys):
        raise StartupGuardError('Project daemon changed during cold-start inspection')
    for name, path in paths.items():
        if _json_file(path, deadline, clock)[1] != snapshots[name]:
            raise StartupGuardError('Startup configuration/process record changed during inspection')
    if checks.voice_is_listening(deadline) is not False:
        raise StartupGuardError('Voice listener appeared during startup inspection')
    sample = checks.memory_sample(deadline); _remaining(deadline, clock)
    total, free, observed = (getattr(sample, key, None) for key in ('total_mib', 'free_mib', 'observed_at'))
    if (getattr(sample, 'gpu_uuid', None) != policy['gpu_uuid'] or type(total) is not int or total != binding['gpu_total_mib']
            or type(free) is not int or not 0 <= free <= total or type(observed) not in (int, float)
            or not math.isfinite(observed) or not 0 <= clock() - observed <= .75):
        raise StartupGuardError('Fresh device memory differs from the calibrated physical GPU')
    evidence['gpu'] = {'available': True, 'gpu_uuid': sample.gpu_uuid, 'total_mib': total, 'free_mib': free,
        'age_ms': round((clock() - observed) * 1000, 2), 'scope': 'device free snapshot; not a physical reservation'}
    evidence['cold_sample'] = {'tts_cold_extra_mib': cold, 'reserve_mib': reserve, 'required_free_mib': cold + reserve,
        'free_mib': free, 'steady_tts_extra_mib': policy.get('tts_extra_mib', 0), 'calibration_id': policy['calibration_id']}
    evidence['extra'].update(project_owner_verified=True, owner_pid=current['pid'],
        ollama_version=runtime['ollama_version'], fit_target_mib=runtime['fit_target_mib'],
        project_model_resident=bool(rows), remaining_startup_ms=round(_remaining(deadline, clock) * 1000, 2))
    if free < cold + reserve:
        evidence.update(status='insufficient_cold_capacity')
        evidence['extra']['controlled_reload_required'] = True
        raise ColdStartupCapacityError(evidence)
    return dict(evidence, status='cold_capacity_available', capacity_verified=True)


@contextmanager
def voice_startup_guard(aura, runtime_root, *, host=HOST, model=MODEL, listen='192.168.50.1',
        port=8792, deadline, checks=None, clock=time.monotonic):
    """Hold through ModelHost construction, warmup, serving and full cleanup."""
    with ServiceInstanceLock(Path(runtime_root) / 'voice8792.instance.lock') as lock:
        evidence = cold_capacity_preflight(aura, runtime_root, lock=lock, host=host, model=model,
            listen=listen, port=port, deadline=deadline, checks=checks, clock=clock)
        yield evidence
