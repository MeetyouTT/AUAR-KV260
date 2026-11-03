"""Fixed-endpoint LAN handoff. Importing this file performs no operations.

The live CLI has no alternate project, endpoint, Python, model or test mode.
Only the existing production manager may start or normally stop its session.
The board probe executes public requests in RAM and opens no media device/DB.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import datetime as dt
import hashlib
import http.client
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
PROJECT = OUT.parents[1]
AURA = PROJECT / 'aura'
HOST = PROJECT / 'deliverables/2026-10-30_board_owner/integration/production_model_host'
BOARD = PROJECT / 'deliverables/2026-10-18_board_dialogue'
CONFIG = AURA / 'config/model_inference.local.json'
MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
WEIGHT_SHA = 'd83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
WEIGHT_SIZE = 14403496864
LOCAL = '127.0.0.1'
LAN = '192.168.50.1'
PEER = '192.168.50.2'
INTERFACE_INDEX = 23
INTERFACE_MAC = 'C8-53-09-B0-89-DA'
INTERFACE_GUID = 'f14f89e5-18f4-483c-b22b-cd8010578636'
PYTHON = Path('D:/AURARuntimes/voice-py310/Scripts/python.exe')
READY = 'READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING'
BOARD_BOOT = '903cfade-b93c-48fa-804e-379be1967313'
MAINTENANCE_CONTRACT = 'explicit_same_session_owned_model_release_before_tts_first_v1'
SESSION = re.compile(r'[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def read(path, limit=1024 * 1024):
    raw = Path(path).read_bytes()
    require(len(raw) <= limit, 'metadata_size_limit')
    return json.loads(raw.decode('utf-8-sig'))


def write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    atomic(path, raw)


def atomic(path, raw):
    path = Path(path)
    temp = path.with_name(path.name + '.part-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def validate_settings(value, host=None):
    fixed = dict(schema_version=1, port=8797, local_health=True,
                 startup_seconds=300, lifetime_seconds=None)
    require(isinstance(value, dict) and set(value) == set(fixed) | {'host', 'allowed_peers', 'voice_python'},
            'fixed_configuration_keys_required')
    require(all(type(value[k]) is type(v) and value[k] == v for k, v in fixed.items()),
            'fixed_configuration_required')
    require((value['host'], value['allowed_peers']) in ((LOCAL, [LOCAL]), (LAN, [PEER])),
            'fixed_endpoint_and_peer_required')
    if host is not None:
        require(value['host'] == host, 'unexpected_endpoint')
    require(isinstance(value['voice_python'], str)
            and Path(value['voice_python']).resolve() == PYTHON.resolve(), 'fixed_voice_python_required')
    return value


def validate_health(value, idle=True):
    require(isinstance(value, dict) and type(value.get('protocol_version')) is int
            and value['protocol_version'] == 1 and value.get('ok') is True
            and value.get('role') == 'model_inference_only'
            and value.get('persistence') == 'none' and value.get('request_logging') is False,
            'healthy_model_only_role_required')
    backend = value.get('backend', {})
    voice = backend.get('voice', {})
    gpu = backend.get('gpu_coordination', {})
    require(backend.get('model') == MODEL and backend.get('tts') == 'omnivoice'
            and type(backend.get('num_step')) is int and backend['num_step'] == 16
            and backend.get('tts_ready') is True and voice.get('alive') is True
            and voice.get('closed') is False and voice.get('quarantined') is False
            and not voice.get('error') and gpu.get('enforcing') is True,
            'original_models_and_live_owned_tts_required')
    if idle:
        require(value.get('active') is False and type(value.get('pending')) is int
                and value['pending'] == 0 and voice.get('request_active') is False
                and gpu.get('queued') == 0 and gpu.get('active') == {'llm': 0, 'tts': 0},
                'current_model_service_must_be_idle')
    return value


def validate_adapter(value):
    require(value.get('index') == INTERFACE_INDEX
            and value.get('description') == 'Intel(R) Ethernet Controller I226-V'
            and value.get('mac_address') == INTERFACE_MAC and value.get('interface_guid') == INTERFACE_GUID
            and value.get('physical') is True and value.get('state') == 'Up'
            and value.get('addresses') == [dict(address=LAN, prefix=24, state='Preferred')]
            and value.get('default_routes') == 0, 'dedicated_physical_ethernet_not_ready')
    return value


def validate_original_residency(rows):
    require(isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict)
            and rows[0].get('name') == MODEL and rows[0].get('model', MODEL) == MODEL
            and type(rows[0].get('context_length')) is int and rows[0]['context_length'] == 2048,
            'original_27b_2048_residency_required')
    return rows


def validate_receipts(directory=OUT, project=PROJECT, *, original_config_sha=None):
    """Require complete original local acceptance; never accepts an old READY alone."""
    directory, project = Path(directory), Path(project)
    status = read(directory / 'STATUS.json')
    ready = read(directory / 'READY_LOCAL.json')
    require(status.get('complete') is True and status.get('phase') == READY
            and status.get('target_endpoint') == 'http://127.0.0.1:8797'
            and status.get('model') == MODEL and status.get('formal_tts') == 'OmniVoice16'
            and all(status.get(key) is True for key in ('environment_validated', 'tts_validated',
                'llm_weights_verified', 'gpu_calibrated_individually', 'local_http_verified')),
            'complete_local_status_required')
    require(ready.get('status') == READY and ready.get('endpoint') == 'http://127.0.0.1:8797'
            and ready.get('model') == MODEL and ready.get('weights_sha256') == WEIGHT_SHA
            and ready.get('tts') == 'Original OmniVoice16 and accepted reference',
            'original_local_ready_required')
    require(all(ready.get(key) is False for key in ('board_accessed_by_deployer', 'audio_played',
                'business_database_opened', 'physical_or_board_acceptance')), 'local_scope_receipt_required')
    validate_health(ready.get('health'), idle=False)
    llm, tts = ready.get('llm_public_probe', {}), ready.get('tts_public_probe', {})
    require(type(llm.get('characters')) is int and llm['characters'] > 0
            and type(tts.get('samples')) is int and tts['samples'] > 0
            and tts.get('sample_rate') == 24000 and SHA.fullmatch(tts.get('sha256', '')),
            'both_public_local_probe_receipts_required')
    verification = read(directory / 'llm_download_verification.json')
    require(verification.get('status') == 'VERIFIED' and verification.get('sha256') == WEIGHT_SHA
            and verification.get('bytes') == WEIGHT_SIZE, 'original_weight_verification_required')
    weights = Path(verification['path']).resolve()
    require(weights.is_relative_to(Path('D:/AIModels').resolve()) and weights.is_file()
            and weights.stat().st_size == WEIGHT_SIZE, 'verified_external_weight_file_required')
    verified_at = dt.datetime.fromisoformat(verification['verified_utc'].replace('Z', '+00:00'))
    require(weights.stat().st_mtime <= verified_at.timestamp() + 1, 'weights_modified_after_sha_verification')
    calibration = read(directory / 'gpu_calibration.json')
    require(calibration.get('status') == 'VALIDATED_LOCAL_BOTH_RESIDENT_PUBLIC_HTTP'
            and calibration.get('policy') == read(project / 'aura/config/gpu_runtime.local.json'),
            'current_measured_gpu_configuration_required')
    require(read(directory / 'tts_calibration.json').get('passed') is True
            and read(directory / 'llm_calibration.json').get('passed') is True,
            'both_measured_calibrations_required')
    manifest = read(directory / 'source_manifest_5090.json')
    require(isinstance(manifest, list) and len(manifest) >= 10, 'deployment_source_manifest_required')
    entries = {}
    for row in manifest:
        require(isinstance(row, dict) and set(row) == {'path', 'sha256'}
                and SHA.fullmatch(row['sha256']), 'invalid_source_manifest')
        name = row['path'].replace('\\', '/')
        path = (project / name).resolve()
        require(path.is_relative_to(project.resolve()) and name not in entries,
                'invalid_source_manifest_path')
        expected = row['sha256']
        if path == (project / 'aura/config/model_inference.local.json').resolve() and original_config_sha:
            require(expected == original_config_sha, 'original_config_not_in_local_acceptance')
        else:
            require(path.is_file() and digest(path.read_bytes()) == expected, 'accepted_source_changed')
        entries[name] = expected
    required = ('aura/config/model_inference.local.json', 'aura/config/gpu_runtime.local.json',
                'aura/config/ollama_runtime.local.json',
                'aura/tools/model_inference_host.py', 'aura/common/model_inference_wire.py',
                'aura/common/inference_output_contract.py',
                'deliverables/2026-10-30_board_owner/integration/production_model_host/production_runtime.py',
                'deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py')
    require(all(name in entries for name in required), 'accepted_manager_and_configs_required')
    return dict(status_sha256=digest((directory / 'STATUS.json').read_bytes()),
                ready_sha256=digest((directory / 'READY_LOCAL.json').read_bytes()),
                manifest_sha256=digest((directory / 'source_manifest_5090.json').read_bytes()),
                accepted_sources=entries, weight_verification_sha256=digest(
                    (directory / 'llm_download_verification.json').read_bytes()),
                weight_sha_recomputed_by_lan_tool=False)


def http_json(host, path, body=None, *, timeout=4, expected_status=200):
    connection = http.client.HTTPConnection(host, 8797, timeout=timeout)
    try:
        encoded = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        connection.request('POST' if body is not None else 'GET', path, encoded,
                           {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(8 * 1024 * 1024 + 1)
        require(response.status == expected_status and len(raw) <= 8 * 1024 * 1024,
                'unexpected_model_http_response')
        return json.loads(raw)
    finally:
        connection.close()


class Live:
    def __init__(self):
        sys.path[:0] = [str(HOST), str(AURA), str(BOARD)]
        self.manage = importlib.import_module('manage')
        self.runtime = importlib.import_module('production_runtime')

    def ps(self, source):
        return self.manage.powershell(source, timeout=15)

    def listeners(self):
        value = self.ps(r'''[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
ConvertTo-Json -InputObject @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in @(8792,8797,11434,11435) } | ForEach-Object {
 [pscustomobject]@{address=$_.LocalAddress;port=[int]$_.LocalPort;pid=[int]$_.OwningProcess}
} | Sort-Object port,address,pid) -Compress''')
        require(isinstance(value, list), 'listener_metadata_unavailable')
        return value

    def process_tree(self):
        value = self.ps(r'''[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
ConvertTo-Json -InputObject @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
 $hash=$null
 if($_.CommandLine){$s=[Security.Cryptography.SHA256]::Create();try{$hash=([BitConverter]::ToString($s.ComputeHash([Text.Encoding]::UTF8.GetBytes($_.CommandLine)))).Replace('-','').ToLowerInvariant()}finally{$s.Dispose()}}
 [pscustomobject]@{pid=[int]$_.ProcessId;ppid=[int]$_.ParentProcessId;created_utc=$_.CreationDate.ToUniversalTime().ToString('o');executable=$_.ExecutablePath;command_sha256=$hash}
}) -Compress''')
        require(isinstance(value, list), 'process_metadata_unavailable')
        return {row['pid']: row for row in value}

    def adapter(self):
        value = self.ps(r'''[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$a=Get-NetAdapter -InterfaceIndex 23 -ErrorAction Stop
$ip=@(Get-NetIPAddress -InterfaceIndex 23 -AddressFamily IPv4 -ErrorAction Stop)
$routes=@(Get-NetRoute -InterfaceIndex 23 -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue)
[pscustomobject]@{index=[int]$a.InterfaceIndex;description=$a.InterfaceDescription;mac_address=([string]$a.MacAddress).ToUpperInvariant();interface_guid=([guid]$a.InterfaceGuid).ToString('D').ToLowerInvariant();physical=[bool]$a.HardwareInterface;state=[string]$a.Status;alias=$a.Name;addresses=@($ip|ForEach-Object{[pscustomobject]@{address=$_.IPAddress;prefix=[int]$_.PrefixLength;state=[string]$_.AddressState}});default_routes=$routes.Count}|ConvertTo-Json -Depth 5 -Compress''')
        return validate_adapter(value)

    def tts(self, owned_pid=None):
        from tools.model_inference_host import WindowsTtsProcessProbe
        return WindowsTtsProcessProbe().read(deadline=time.monotonic() + 4., owned_pid=owned_pid)

    def protected(self, listeners=None):
        rows = self.listeners() if listeners is None else listeners
        protected = [row for row in rows if row['port'] == 11434]
        owners = [self.manage.process(pid) for pid in sorted({row['pid'] for row in protected})]
        require(all(owner is not None for owner in owners), 'protected_listener_owner_unavailable')
        from project_ollama import inspect_ownership
        fixed = inspect_ownership()
        return dict(default_ollama_listeners=protected, default_ollama_owners=owners,
                    fixed_daemon={key: fixed[key] for key in ('pid', 'creation_utc', 'executable',
                                                              'command_line', 'listeners')})

    def snapshot(self, host=None, *, original_config_sha=None):
        receipts = validate_receipts(original_config_sha=original_config_sha)
        settings, config_sha = self.runtime.config()
        validate_settings(settings, host)
        require(Path(sys.executable).resolve() == PYTHON.resolve(), 'run_with_formal_voice_python')
        record, state = self.manage.latest()
        require(record is not None and state is not None and state.get('status') == 'READY'
                and self.manage.same_owner(record), 'fresh_live_ready_owner_required')
        require(record.get('configuration_sha256') == config_sha == state.get('configuration_sha256')
                and record.get('runner_sha256') == digest((HOST / 'production_runtime.py').read_bytes())
                and record.get('lifetime_seconds') is None and record.get('scheduled_task_created') is False,
                'accepted_current_owner_configuration_required')
        require(state.get('session_id') == record['session_id'] and state.get('role') == 'model_inference_only'
                and state.get('owner_protocol') == 'aura.production-model-owner-1'
                and state.get('listen') == settings['host'] and state.get('port') == 8797
                and state.get('model') == MODEL and state.get('lifetime_seconds') is None
                and all(state.get(key) is False for key in ('business_database_opened', 'request_logging', 'raw_audio_archived')),
                'current_model_only_owner_required')
        startup = state.get('startup', {})
        require(startup.get('ready') is True and startup.get('same_tts_process') is True
                and startup.get('memory_only') is True and startup.get('automatic_unload') is False,
                'completed_original_startup_required')
        require(Path(state.get('control_path', '')).resolve() ==
                (HOST / 'sessions' / record['session_id'] / 'CONTROL.json').resolve(), 'session_control_path_changed')
        require(not Path(state['control_path']).exists(), 'control_request_already_pending')
        tree = self.process_tree()
        def descendant(pid, ancestor):
            visited = set()
            while pid in tree and pid not in visited:
                if pid == ancestor:
                    return True
                visited.add(pid)
                pid = tree[pid]['ppid']
            return False
        require(type(state.get('pid')) is int and type(state.get('same_unique_tts_pid')) is int
                and descendant(state['pid'], record['owner']['pid'])
                and descendant(state['same_unique_tts_pid'], state['pid']), 'owner_and_tts_process_family_changed')
        main_owner = self.manage.process(state['pid'])
        tts_owner = self.manage.process(state['same_unique_tts_pid'])
        require(main_owner is not None and tts_owner is not None, 'current_owned_process_missing')
        ownership = self.tts(state['same_unique_tts_pid'])
        require(ownership.get('available') is True and ownership.get('logical_workers') == 1
                and ownership.get('owned_workers') == 1 and ownership.get('external_workers') == 0,
                'exactly_one_owned_tts_required')
        listeners = self.listeners()
        require(not any(row['port'] == 8792 for row in listeners), 'legacy_business_listener_present')
        require([row for row in listeners if row['port'] == 8797] ==
                [dict(address=settings['host'], port=8797, pid=state['pid'])], 'listener_owner_or_bind_changed')
        health = validate_health(self.manage.health())
        validate_original_residency(self.runtime.ollama_json('GET', '/api/ps').get('models'))
        protected = self.protected(listeners)
        require(protected['fixed_daemon'] == {key: state['fixed_daemon_owner'][key]
                for key in protected['fixed_daemon']}, 'project_ollama_owner_changed')
        again, again_state = self.manage.latest()
        require(again == record and again_state.get('session_id') == state['session_id']
                and again_state.get('status') == 'READY' and self.manage.same_owner(record),
                'service_owner_changed_during_inspection')
        return dict(schema='aura-5090-lan-inspection-1', status='FRESH_IDLE_MODEL_OWNER_CONFIRMED', utc=utc(),
                    session_id=record['session_id'], configuration_sha256=config_sha, endpoint=f'http://{settings["host"]}:8797',
                    settings=settings, record=record, main_owner=main_owner, tts_owner=tts_owner,
                    tts_ownership=ownership, state=state, health=health, listeners=listeners,
                    protected=protected, local_acceptance=receipts, microphone_or_playback_opened=False,
                    business_database_opened=False, model_inference_request_sent=False)

    def require_model_absent(self, expected_daemon_owner):
        """Read-only TTS-first gate. Never unloads or adopts any model."""
        current = self.protected()['fixed_daemon']
        require(current == expected_daemon_owner, 'fixed_daemon_owner_changed_no_start')
        rows = self.runtime.ollama_json('GET', '/api/ps').get('models')
        require(isinstance(rows, list) and rows == [], 'model_still_resident_tts_first_start_refused')
        require(self.protected()['fixed_daemon'] == expected_daemon_owner,
                'fixed_daemon_changed_during_empty_residency_check')
        return dict(utc=utc(), fixed_daemon_owner=expected_daemon_owner,
                    models=[], tts_first_model_absence_confirmed=True, read_only=True)

    def normal_stop(self, expected, *, release_owned_model, expected_daemon_owner):
        record, state = self.manage.latest()
        require(record == expected and self.manage.same_owner(record), 'expected_owner_changed_before_stop')
        require(type(release_owned_model) is bool, 'explicit_stop_release_mode_required')
        if release_owned_model:
            require(state and state.get('session_id') == record['session_id'] and state.get('status') == 'READY'
                    and state.get('owns_fixed_model') is True, 'ready_same_session_owned_model_release_required')
            require({key: state.get('fixed_daemon_owner', {}).get(key) for key in expected_daemon_owner}
                    == expected_daemon_owner and self.protected()['fixed_daemon'] == expected_daemon_owner,
                    'release_fixed_daemon_owner_changed')
            validate_health(self.manage.health())
            # The original runtime proves its state/daemon/model ownership; its
            # read-only HTTP helper additionally binds actual context to 2048.
            require(self.runtime.require_owned_model(state) is True, 'owned_resident_model_required_for_release')
            validate_original_residency(self.runtime.ollama_json('GET', '/api/ps').get('models'))
        else:
            # Only unfinished candidate cleanup can stop without model release.
            # A resident model makes this path fail before any control request.
            require(state and state.get('status') in ('STARTING', 'FAILED'),
                    'no_release_stop_only_for_unfinished_candidate')
            self.require_model_absent(expected_daemon_owner)
        result = self.manage.stop(release=release_owned_model, wait_seconds=40)
        require(result.get('status') == 'CLOSED' and result.get('session_id') == expected['session_id']
                and result.get('forced_action') is False and result.get('state', {}).get('server_closed') is True
                and result['state'].get('owned_tts_closed') is True
                and result['state'].get('stop_reason') in
                    (('release_owned_model',) if release_owned_model else ('stop', 'explicit_startup_cancel'))
                and result['state'].get('fixed_daemon_stopped', False) is False
                and result['state'].get('unrelated_models_stopped', False) is False,
                'normal_owned_server_and_tts_close_unconfirmed')
        if release_owned_model:
            released = result['state'].get('model_release', {})
            require(released.get('released') is True and released.get('model') == MODEL
                    and released.get('project_daemon_stopped') is False
                    and released.get('unrelated_models_stopped') is False,
                    'explicit_owned_model_release_receipt_required')
        require(not self.manage.same_owner(expected), 'old_owner_still_alive')
        self.require_vacant()
        result['tts_first_model_absence'] = self.require_model_absent(expected_daemon_owner)
        return result

    def require_vacant(self):
        require(not any(row['port'] in (8792, 8797) for row in self.listeners()), 'old_or_foreign_listener_present')
        ownership = self.tts()
        require(ownership.get('available') is True and ownership.get('logical_workers') == 0,
                'old_or_foreign_tts_still_present_no_takeover')
        return ownership


@contextmanager
def operation_lock():
    require(os.name == 'nt', 'windows_only')
    import msvcrt
    with (HERE / 'lan_operation.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError('another_lan_operation_is_active') from error
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def transaction_path(identifier):
    require(SESSION.fullmatch(identifier) is not None, 'explicit_transaction_id_required')
    return HERE / 'transactions' / identifier


def load_transaction(identifier):
    path = transaction_path(identifier)
    value = read(path / 'transaction.json')
    require(value.get('schema') == 'aura-5090-lan-transaction-1' and value.get('transaction_id') == identifier,
            'invalid_transaction_receipt')
    before = (path / 'local_config.before.json').read_bytes()
    require(digest(before) == value['original_config_sha256'], 'original_configuration_backup_changed')
    validate_settings(json.loads(before), LOCAL)
    return path, value, before


def capture_candidate(live, value):
    record, state = live.manage.latest()
    if (record and record['session_id'] != value['before']['session_id']
            and record.get('configuration_sha256') == value['lan_config_sha256']
            and record.get('runner_sha256') == value['before']['record']['runner_sha256']
            and dt.datetime.fromisoformat(record['created_utc']) >= dt.datetime.fromisoformat(value['started_utc'])):
        value['candidate_record'] = record


def switch(live, expected_session, expected_config_sha, *, explicit_controlled_model_release=False):
    require(explicit_controlled_model_release is True, 'explicit_controlled_model_release_authorization_required')
    before = live.snapshot(LOCAL)
    require(before['session_id'] == expected_session and before['configuration_sha256'] == expected_config_sha,
            'inspection_owner_or_config_changed')
    require(before['state'].get('owns_fixed_model') is True, 'current_session_must_own_fixed_model')
    adapter = live.adapter()
    original = CONFIG.read_bytes()
    require(digest(original) == expected_config_sha, 'configuration_changed_before_handoff')
    settings = dict(before['settings'], host=LAN, allowed_peers=[PEER])
    validate_settings(settings, LAN)
    lan_raw = (json.dumps(settings, ensure_ascii=False, indent=2) + '\n').encode()
    identifier = uuid.uuid4().hex
    path = transaction_path(identifier)
    path.mkdir(parents=True, exist_ok=False)
    atomic(path / 'local_config.before.json', original)
    value = dict(schema='aura-5090-lan-transaction-1', transaction_id=identifier,
                 started_utc=utc(), phase='LOCAL_OWNER_RECHECK_PENDING', before=before, adapter=adapter,
                 original_config_sha256=expected_config_sha, lan_config_sha256=digest(lan_raw),
                 maintenance_contract=MAINTENANCE_CONTRACT, explicit_controlled_model_release=True,
                 forced_action=False, firewall_modified=False,
                 board_modified=False, playback_or_recording_performed=False)
    write(path / 'transaction.json', value)
    try:
        recheck = live.snapshot(LOCAL)
        require(recheck['record'] == before['record'] and recheck['protected'] == before['protected'],
                'owner_changed_before_normal_stop')
        value['normal_stop'] = live.normal_stop(before['record'], release_owned_model=True,
                                               expected_daemon_owner=before['protected']['fixed_daemon'])
        value['phase'] = 'LOCAL_SERVER_TTS_CLOSED_AND_OWNED_MODEL_RELEASED'
        write(path / 'transaction.json', value)
        require(live.protected() == before['protected'], 'protected_ollama_changed_no_config_write')
        value['lan_prestart_model_absence'] = live.require_model_absent(before['protected']['fixed_daemon'])
        require(CONFIG.read_bytes() == original, 'configuration_changed_no_overwrite')
        atomic(CONFIG, lan_raw)
        value['phase'] = 'LAN_CONFIGURATION_WRITTEN_START_PENDING'
        write(path / 'transaction.json', value)
        live.require_model_absent(before['protected']['fixed_daemon'])
        result = live.manage.start(wait_seconds=320)
        capture_candidate(live, value)
        require(result.get('status') == 'STARTED' and value.get('candidate_record') is not None,
                'fresh_lan_session_not_confirmed')
        after = live.snapshot(LAN, original_config_sha=expected_config_sha)
        require(after['record'] == value['candidate_record'] and after['session_id'] != before['session_id']
                and after['main_owner'] != before['main_owner'] and after['tts_owner'] != before['tts_owner']
                and after['protected'] == before['protected'] and after['state'].get('owns_fixed_model') is True,
                'fresh_lan_or_protected_owner_mismatch')
        denied = http_json(LAN, '/v1/inference/llm', {}, expected_status=403)
        require(denied.get('error', {}).get('code') == 'peer_denied', 'local_inference_not_denied')
        value.update(phase='LAN_READY_FIREWALL_AND_BOARD_PROBE_PENDING', completed_utc=utc(), after=after,
                     local_post_denied=True, board_accessed=False)
        write(path / 'transaction.json', value)
        return dict(status=value['phase'], transaction_id=identifier, session_id=after['session_id'],
                    endpoint=after['endpoint'], configuration_sha256=after['configuration_sha256'],
                    receipt=str(path / 'transaction.json'), explicit_controlled_model_release=True,
                    firewall_modified=False, board_accessed=False)
    except BaseException as error:
        value['failed_phase'] = value['phase']
        value.update(phase='SWITCH_FAILED_REVIEW_EXACT_RECEIPT_BEFORE_ROLLBACK', failed_utc=utc(),
                     error_type=type(error).__name__, error_code=str(error)[:160])
        try:
            capture_candidate(live, value)
        except Exception:
            pass
        write(path / 'transaction.json', value)
        error.lan_transaction_id = identifier
        error.lan_receipt = str(path / 'transaction.json')
        raise


def rollback(live, identifier, expected_session, *, explicit_controlled_model_release=False):
    require(explicit_controlled_model_release is True, 'explicit_controlled_model_release_authorization_required')
    path, value, original = load_transaction(identifier)
    require(value.get('maintenance_contract') == MAINTENANCE_CONTRACT
            and value.get('explicit_controlled_model_release') is True,
            'legacy_transaction_frozen_requires_new_authorization')
    validate_receipts(original_config_sha=value['original_config_sha256'])
    require(value.get('phase') != 'ROLLED_BACK_LOCAL_READY', 'transaction_already_rolled_back')
    current, state = live.manage.latest()
    permitted = value.get('candidate_record', value['before']['record'])
    require(current == permitted and current['session_id'] == expected_session,
            'rollback_refuses_a_different_or_unrecorded_owner')
    raw = CONFIG.read_bytes()
    require(digest(raw) in (value['original_config_sha256'], value['lan_config_sha256']),
            'rollback_refuses_changed_configuration')
    require(live.protected() == value['before']['protected'], 'rollback_protected_owner_changed')
    if live.manage.same_owner(current):
        require(current != value['before']['record'], 'rollback_refuses_stopping_original_local_owner')
        if state and state.get('status') == 'READY':
            snapshot = live.snapshot(LAN, original_config_sha=value['original_config_sha256'])
            require(snapshot['record'] == permitted, 'rollback_owner_changed')
            require(snapshot['state'].get('owns_fixed_model') is True,
                    'rollback_live_session_does_not_own_resident_model')
            release = True
        else:
            require(state and state.get('session_id') == current['session_id']
                    and state.get('status') in ('STARTING', 'FAILED')
                    and current.get('configuration_sha256') == value['lan_config_sha256'],
                    'rollback_starting_owner_not_proven')
            live.require_model_absent(value['before']['protected']['fixed_daemon'])
            release = False
        value['rollback_normal_stop'] = live.normal_stop(current, release_owned_model=release,
                                                        expected_daemon_owner=value['before']['protected']['fixed_daemon'])
    else:
        live.require_vacant()
        # A dead owner cannot accept its session-bound release request. A
        # remaining model needs a separately authorized ownership-chain repair.
        live.require_model_absent(value['before']['protected']['fixed_daemon'])
    value['rollback_prestart_model_absence'] = live.require_model_absent(value['before']['protected']['fixed_daemon'])
    require(CONFIG.read_bytes() == raw, 'configuration_changed_during_rollback')
    atomic(CONFIG, original)
    value['phase'] = 'ORIGINAL_LOCAL_CONFIG_RESTORED_START_PENDING'
    write(path / 'transaction.json', value)
    live.require_model_absent(value['before']['protected']['fixed_daemon'])
    result = live.manage.start(wait_seconds=320)
    require(result.get('status') == 'STARTED', 'fresh_local_rollback_session_required')
    after = live.snapshot(LOCAL)
    require(after['session_id'] not in (current['session_id'], value['before']['session_id'])
            and after['protected'] == value['before']['protected'] and after['state'].get('owns_fixed_model') is True,
            'rollback_owner_or_protected_process_mismatch')
    value.update(phase='ROLLED_BACK_LOCAL_READY', rollback_utc=utc(), rollback_after=after,
                 firewall_rollback_separate_and_receipt_bound=True)
    write(path / 'transaction.json', value)
    return dict(status=value['phase'], transaction_id=identifier, session_id=after['session_id'],
                endpoint=after['endpoint'], receipt=str(path / 'transaction.json'),
                explicit_controlled_model_release=True, firewall_modified=False)


def board_script():
    """The exact production wire validators execute only in board process RAM."""
    source = (HERE / 'board_public_probe.py').read_text(encoding='utf-8')
    contracts = {name: base64.b64encode((AURA / 'common' / (name + '.py')).read_bytes()).decode()
                 for name in ('inference_output_contract', 'model_inference_wire')}
    return ('CONTRACT_SOURCES = ' + repr(contracts) + '\nEXPECTED_BOOT = ' + repr(BOARD_BOOT)
            + '\n' + source)


def probe_board(live, identifier, expected_session):
    path, value, original = load_transaction(identifier)
    require(value.get('phase') == 'LAN_READY_FIREWALL_AND_BOARD_PROBE_PENDING', 'completed_lan_handoff_required')
    before = live.snapshot(LAN, original_config_sha=value['original_config_sha256'])
    require(before['session_id'] == expected_session and before['record'] == value['candidate_record'],
            'board_probe_current_owner_changed')
    firewall = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                              '-File', str(OUT / 'configure_model_firewall.ps1'), '-Action', 'Check',
                              '-ExpectedSession', expected_session], capture_output=True, timeout=600,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(firewall.returncode == 0, 'exact_firewall_rule_check_required')
    from board_ssh import ssh
    report = json.loads(ssh('python3 -B -', board_script(), timeout=300))
    require(report.get('status') == 'PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS'
            and report.get('board_boot_id') == BOARD_BOOT
            and report.get('audio_device_opened') is False and report.get('business_database_opened') is False
            and report.get('board_file_modified') is False, 'board_public_probe_failed')
    after = live.snapshot(LAN, original_config_sha=value['original_config_sha256'])
    require(after['record'] == before['record'] and after['tts_owner'] == before['tts_owner']
            and after['protected'] == before['protected'], 'owner_changed_during_board_probe')
    report.update(host_observed_utc=utc(), host_session_id=expected_session,
                  local_tts_same_owner=True, protected_ollama_same_owner=True,
                  physical_playback_or_dialogue_acceptance=False)
    write(path / 'board_public_probe.json', report)
    value.update(phase='LAN_PUBLIC_BOARD_MODEL_PROBE_PASS_PHYSICAL_ACCEPTANCE_PENDING',
                 board_probe_receipt='board_public_probe.json', board_probe_utc=utc())
    write(path / 'transaction.json', value)
    return dict(status=value['phase'], transaction_id=identifier, session_id=expected_session,
                receipt=str(path / 'board_public_probe.json'), audio_played=False)


def inspection(live, expected_session=None):
    settings = validate_settings(read(CONFIG))
    if settings['host'] == LOCAL:
        snapshot = live.snapshot(LOCAL)
    else:
        matches = []
        for candidate in (HERE / 'transactions').glob('*/transaction.json'):
            transaction = read(candidate)
            if transaction.get('candidate_record', {}).get('session_id') == expected_session:
                matches.append(transaction)
        require(len(matches) == 1, 'explicit_recorded_lan_session_required')
        snapshot = live.snapshot(LAN, original_config_sha=matches[0]['original_config_sha256'])
        require(snapshot['record'] == matches[0]['candidate_record'], 'recorded_lan_owner_changed')
    if expected_session:
        require(snapshot['session_id'] == expected_session, 'expected_current_session_required')
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'firewall-guard', 'switch', 'rollback', 'probe-board'))
    parser.add_argument('--expected-session')
    parser.add_argument('--expected-config-sha')
    parser.add_argument('--transaction')
    parser.add_argument('--execute', action='store_true', help='Explicitly perform the chosen handoff/rollback/probe')
    parser.add_argument('--explicit-controlled-model-release', action='store_true',
                        help='Authorize only the same-session owned fixed-model maintenance release for TTS-first restart')
    args = parser.parse_args()
    if args.expected_session:
        require(SESSION.fullmatch(args.expected_session) is not None, 'explicit_session_id_required')
    live = Live()
    if args.action in ('inspect', 'firewall-guard'):
        result = inspection(live, args.expected_session)
        if args.action == 'firewall-guard':
            adapter = live.adapter()
            result = {key: result[key] for key in ('status', 'utc', 'session_id', 'configuration_sha256',
                                                   'endpoint', 'main_owner', 'tts_owner', 'health',
                                                   'tts_ownership', 'listeners', 'local_acceptance')}
            result['adapter'] = adapter
        else:
            write(HERE / 'latest_inspection.json', result)
            result = {key: result[key] for key in ('status', 'utc', 'session_id', 'configuration_sha256', 'endpoint')}
            result['receipt'] = str(HERE / 'latest_inspection.json')
    else:
        require(args.execute and args.expected_session, 'explicit_execution_and_current_session_required')
        with operation_lock():
            if args.action == 'switch':
                require(args.expected_config_sha and SHA.fullmatch(args.expected_config_sha), 'explicit_config_sha_required')
                result = switch(live, args.expected_session, args.expected_config_sha,
                                explicit_controlled_model_release=args.explicit_controlled_model_release)
            elif args.action == 'rollback':
                require(args.transaction, 'explicit_transaction_required')
                result = rollback(live, args.transaction, args.expected_session,
                                  explicit_controlled_model_release=args.explicit_controlled_model_release)
            else:
                require(args.transaction, 'explicit_transaction_required')
                result = probe_board(live, args.transaction, args.expected_session)
    # ASCII JSON survives native stdout decoding in fresh Windows/UAC code pages.
    # JSON parsers restore the exact Unicode adapter alias used by strict guards.
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        result = dict(status='REFUSED_OR_FAILED', error_type=type(error).__name__, code=str(error)[:180])
        if getattr(error, 'lan_transaction_id', None):
            result.update(transaction_id=error.lan_transaction_id, receipt=error.lan_receipt)
        print(json.dumps(result))
        sys.exit(1)
