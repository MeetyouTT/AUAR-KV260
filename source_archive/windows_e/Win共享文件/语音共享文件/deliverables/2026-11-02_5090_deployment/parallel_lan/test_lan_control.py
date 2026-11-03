"""Isolated handoff failures, real loopback HTTP ACL and production wire tests.

The lifecycle manager below is fake. No live model, firewall or board is used.
All temporary configuration writes stay beneath parallel_lan/test_work_*.
"""
import base64
import copy
import http.client
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import lan_control as lan

sys.path.insert(0, str(lan.AURA))
from common.model_inference_wire import Owner, WireError, audio_payload, decode_audio, validate_response
from tools.model_inference_host import make_server


def local_settings():
    return dict(schema_version=1, host=lan.LOCAL, port=8797, allowed_peers=[lan.LOCAL], local_health=True,
                startup_seconds=300, lifetime_seconds=None, voice_python=str(lan.PYTHON))


def healthy():
    return dict(protocol_version=1, ok=True, role='model_inference_only', persistence='none',
                request_logging=False, active=False, pending=0,
                backend=dict(model=lan.MODEL, tts='omnivoice', num_step=16, tts_ready=True,
                             voice=dict(alive=True, closed=False, quarantined=False, error='', request_active=False),
                             gpu_coordination=dict(enforcing=True, queued=0, active={'llm': 0, 'tts': 0})))


class FakeRuntime:
    def __init__(self, live):
        self.live = live

    def require_owned_model(self, state):
        lan.require(state.get('owns_fixed_model') is True, 'fake_model_not_owned')
        lan.require(state['fixed_daemon_owner'] == self.live.protected()['fixed_daemon'], 'fake_daemon_changed')
        lan.require(len(self.live.model_rows) <= 1
                    and all(row.get('name') == lan.MODEL for row in self.live.model_rows), 'fake_foreign_model')
        return bool(self.live.model_rows)

    def ollama_json(self, method, path):
        if (method, path) != ('GET', '/api/ps'):
            raise AssertionError('The LAN controller may only inspect model residency')
        return {'models': copy.deepcopy(self.live.model_rows)}


class FakeManager:
    def __init__(self, live):
        self.live = live
        self.calls = []
        self.counter = 0
        self.record = dict(session_id='a' * 32, configuration_sha256=lan.digest(lan.CONFIG.read_bytes()),
                           runner_sha256='d' * 64, created_utc='2026-01-01T00:00:00+00:00', owner={'pid': 11})
        self.alive = True
        self.fail_start = False
        self.fail_start_after_model_load = False
        self.missing_release_receipt = False
        self.leave_model_resident = False
        self.state_status = 'READY'
        self.closed_state = None

    def state(self):
        return dict(session_id=self.record['session_id'], status=self.state_status,
                    owns_fixed_model=self.live.owns_model,
                    fixed_daemon_owner=copy.deepcopy(getattr(self, 'state_daemon_override', self.live.fixed_daemon)))

    def latest(self):
        return self.record, self.state()

    def health(self):
        value = healthy()
        value['active'] = self.live.busy
        return value

    def same_owner(self, expected):
        return expected == self.record and self.alive

    def start(self, *, wait_seconds):
        lan.require(self.live.model_rows == [], 'fake_original_tts_first_requires_no_resident_model')
        self.calls.append(('start', wait_seconds))
        self.counter += 1
        self.record = dict(session_id=('b' if self.counter == 1 else 'c') * 32,
                           configuration_sha256=lan.digest(lan.CONFIG.read_bytes()),
                           runner_sha256='d' * 64, created_utc=lan.utc(), owner={'pid': 22 + self.counter})
        self.alive = True
        self.live.owns_model = False
        self.state_status = 'STARTING'
        if self.fail_start:
            self.fail_start = False
            self.alive = False
            self.state_status = 'FAILED'
            raise RuntimeError('isolated_start_failure')
        self.live.model_rows = [dict(name=lan.MODEL, model=lan.MODEL, context_length=2048)]
        self.live.owns_model = True
        if self.fail_start_after_model_load:
            self.fail_start_after_model_load = False
            self.alive = False
            self.state_status = 'FAILED'
            raise RuntimeError('isolated_post_model_start_failure')
        self.state_status = 'READY'
        return dict(status='STARTED', session_id=self.record['session_id'])

    def stop(self, *, release, wait_seconds):
        lan.require(self.alive, 'fake_owner_changed')
        self.calls.append(('normal_stop', release))
        self.live.closed.append(copy.deepcopy(self.record))
        if release:
            lan.require(self.state_status == 'READY', 'fake_release_requires_ready')
            self.live.runtime.require_owned_model(self.state())
            if not self.leave_model_resident:
                self.live.model_rows = []
        self.alive = False
        self.state_status = 'CLOSED'
        state = dict(status='CLOSED', server_closed=True, owned_tts_closed=True,
                     stop_reason='release_owned_model' if release else 'stop',
                     fixed_daemon_stopped=False, unrelated_models_stopped=False)
        if release and not self.missing_release_receipt:
            state['model_release'] = dict(released=True, model=lan.MODEL, was_resident=True,
                                         project_daemon_stopped=False, unrelated_models_stopped=False)
        self.closed_state = copy.deepcopy(state)
        return dict(status='CLOSED', session_id=self.record['session_id'], forced_action=False, state=state)


class FakeLive(lan.Live):
    def __init__(self):
        self.fixed_daemon = dict(pid=31, creation_utc='2026-01-01T00:00:00+00:00', executable='D:/ollama.exe',
                                 command_line='ollama.exe serve', listeners=[{'port': 11435}])
        self.model_rows = [dict(name=lan.MODEL, model=lan.MODEL, context_length=2048)]
        self.owns_model = True
        self.busy = False
        self.runtime = FakeRuntime(self)
        self.manage = FakeManager(self)
        self.closed = []
        self.changed_protected = False

    def snapshot(self, host, *, original_config_sha=None):
        settings = lan.validate_settings(lan.read(lan.CONFIG), host)
        lan.require(self.manage.alive, 'fake_owner_exited')
        return dict(session_id=self.manage.record['session_id'], record=copy.deepcopy(self.manage.record),
                    configuration_sha256=lan.digest(lan.CONFIG.read_bytes()), settings=settings,
                    endpoint='http://' + host + ':8797', main_owner={'pid': self.manage.record['owner']['pid']},
                    tts_owner={'pid': self.manage.record['owner']['pid'] + 100}, protected=self.protected(),
                    state=self.manage.state())

    def adapter(self):
        return {'index': lan.INTERFACE_INDEX}

    def protected(self):
        return {'fixed_daemon': copy.deepcopy(self.fixed_daemon), 'default_ollama': 2 + int(self.changed_protected)}

    def require_vacant(self):
        lan.require(not self.manage.alive, 'fake_listener_present')


class GuardTests(unittest.TestCase):
    def test_exact_physical_adapter_not_old_reassigned_index(self):
        value = dict(index=23, description='Intel(R) Ethernet Controller I226-V',
                     mac_address=lan.INTERFACE_MAC, interface_guid=lan.INTERFACE_GUID, physical=True,
                     state='Up', addresses=[dict(address=lan.LAN, prefix=24, state='Preferred')], default_routes=0)
        lan.validate_adapter(value)
        for changes in ({'index': 22}, {'physical': False}, {'mac_address': '00-00-00-00-00-00'},
                        {'interface_guid': '00000000-0000-0000-0000-000000000000'},
                        {'description': 'WAN Miniport (Network Monitor)'}, {'default_routes': 1},
                        {'addresses': [dict(address=lan.LAN, prefix=16, state='Preferred')]},
                        {'addresses': value['addresses'] + [dict(address='192.168.50.99', prefix=24, state='Preferred')]}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                lan.validate_adapter(dict(value, **changes))

    def test_adapter_collection_does_not_hide_additional_ipv4(self):
        live = object.__new__(lan.Live)
        value = dict(index=23, description='Intel(R) Ethernet Controller I226-V',
                     mac_address=lan.INTERFACE_MAC, interface_guid=lan.INTERFACE_GUID, physical=True,
                     state='Up', addresses=[dict(address=lan.LAN, prefix=24, state='Preferred'),
                     dict(address='192.168.50.99', prefix=24, state='Preferred')], default_routes=0)
        queries = []
        def fake_powershell(source):
            queries.append(source)
            result = copy.deepcopy(value)
            # Simulate the cmdlet: an address filter would conceal the extra IP.
            if '-IPAddress ' in source:
                result['addresses'] = result['addresses'][:1]
            return result
        live.ps = fake_powershell
        with self.assertRaisesRegex(RuntimeError, 'dedicated_physical_ethernet_not_ready'):
            live.adapter()
        self.assertEqual(len(queries), 1)

    def test_fixed_settings_accept_only_both_exact_pairs(self):
        value = local_settings()
        lan.validate_settings(value, lan.LOCAL)
        lan.validate_settings(dict(value, host=lan.LAN, allowed_peers=[lan.PEER]), lan.LAN)
        for changes in ({'host': '0.0.0.0'}, {'allowed_peers': [lan.LOCAL, lan.PEER]}, {'port': 8792},
                        {'local_health': False}, {'lifetime_seconds': 7200}, {'startup_seconds': 301},
                        {'schema_version': True}, {'voice_python': 'C:/unowned/python.exe'}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                lan.validate_settings(dict(value, **changes))

    def test_current_health_refuses_busy_wrong_or_unready_models(self):
        lan.validate_health(healthy())
        for key, changed in [('active', True), ('pending', 1), ('request_logging', True), ('ok', False)]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                lan.validate_health(dict(healthy(), **{key: changed}))
        for key, changed in [('num_step', 8), ('tts_ready', False), ('model', 'other-model')]:
            value = healthy()
            value['backend'][key] = changed
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                lan.validate_health(value)

    def test_incomplete_status_refused_before_any_runtime_or_weight_access(self):
        good_ready = dict(status=lan.READY)
        for status in ({'complete': False, 'phase': lan.READY}, {'complete': True, 'phase': 'STARTING'},
                       {'complete': 1, 'phase': lan.READY}):
            with patch.object(lan, 'read', side_effect=[status, good_ready]), self.assertRaisesRegex(RuntimeError, 'complete_local_status_required'):
                lan.validate_receipts()

    def test_metadata_path_cannot_escape_transactions(self):
        for value in ('../other', 'b' * 31, 'B' * 32, 'b' * 32 + '/next'):
            with self.assertRaises(RuntimeError):
                lan.transaction_path(value)

    def test_complete_receipts_require_current_source_and_weight_identity(self):
        work = Path(tempfile.mkdtemp(prefix='test_work_receipts_', dir=lan.HERE))
        project, directory = work / 'project', work / 'deployment'
        directory.mkdir()
        names = ('aura/config/model_inference.local.json', 'aura/config/gpu_runtime.local.json',
                 'aura/config/ollama_runtime.local.json',
                 'aura/tools/model_inference_host.py', 'aura/common/model_inference_wire.py',
                 'aura/common/inference_output_contract.py',
                 'deliverables/2026-10-30_board_owner/integration/production_model_host/production_runtime.py',
                 'deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py',
                 'start_model_dashboard.ps1', 'deliverables/2026-10-18_board_dialogue/board_ssh.py')
        for name in names:
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'{}' if name.endswith('.json') else b'# isolated source fixture\n')
        policy = {'isolated': True}
        lan.write(project / names[1], policy)
        lan.write(directory / 'STATUS.json', dict(complete=True, phase=lan.READY,
                  target_endpoint='http://127.0.0.1:8797', model=lan.MODEL, formal_tts='OmniVoice16',
                  environment_validated=True, tts_validated=True, llm_weights_verified=True,
                  gpu_calibrated_individually=True, local_http_verified=True))
        lan.write(directory / 'READY_LOCAL.json', dict(status=lan.READY, endpoint='http://127.0.0.1:8797',
                  model=lan.MODEL, weights_sha256=lan.WEIGHT_SHA, tts='Original OmniVoice16 and accepted reference',
                  board_accessed_by_deployer=False, audio_played=False, business_database_opened=False,
                  physical_or_board_acceptance=False, health=healthy(), llm_public_probe={'characters': 5},
                  tts_public_probe={'samples': 24, 'sample_rate': 24000, 'sha256': '1' * 64}))
        weights = Path('D:/AIModels/parallel_lan_isolated_virtual_weight.gguf').resolve()
        lan.write(directory / 'llm_download_verification.json', dict(status='VERIFIED', sha256=lan.WEIGHT_SHA,
                  bytes=lan.WEIGHT_SIZE, path=str(weights), verified_utc='2026-11-01T00:00:00+00:00'))
        lan.write(directory / 'gpu_calibration.json', {'status': 'VALIDATED_LOCAL_BOTH_RESIDENT_PUBLIC_HTTP', 'policy': policy})
        for name in ('llm_calibration.json', 'tts_calibration.json'):
            lan.write(directory / name, {'passed': True})
        # Windows deploy_5090 emits backslashes; canonical names must still bind.
        lan.write(directory / 'source_manifest_5090.json', [dict(path=name.replace('/', '\\'),
                  sha256=lan.digest((project / name).read_bytes())) for name in names])
        original_stat = Path.stat
        def virtual_weight_stat(path, **kwargs):
            if path == weights:
                return SimpleNamespace(st_mode=stat.S_IFREG, st_size=lan.WEIGHT_SIZE, st_mtime=0)
            return original_stat(path, **kwargs)
        with patch.object(Path, 'stat', virtual_weight_stat):
            result = lan.validate_receipts(directory, project)
            self.assertIn(names[0], result['accepted_sources'])
            (project / 'deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py').write_bytes(b'# changed manager\n')
            with self.assertRaisesRegex(RuntimeError, 'accepted_source_changed'):
                lan.validate_receipts(directory, project)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='test_work_', dir=lan.HERE))
        self.config = self.work / 'model_inference.local.json'
        self.original = (json.dumps(local_settings(), indent=2) + '\n').encode()
        self.config.write_bytes(self.original)
        self.patches = [patch.object(lan, 'HERE', self.work), patch.object(lan, 'CONFIG', self.config),
                        patch.object(lan, 'validate_receipts', return_value={}),
                        patch.object(lan, 'http_json', return_value={'error': {'code': 'peer_denied'}})]
        for item in self.patches:
            item.start()
        self.live = FakeLive()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        # Retain test folders as isolated evidence; no production paths removed.

    def handoff(self):
        return lan.switch(self.live, 'a' * 32, lan.digest(self.original), explicit_controlled_model_release=True)

    def test_normal_stop_fresh_start_and_exact_byte_rollback(self):
        result = self.handoff()
        self.assertEqual(self.live.manage.calls, [('normal_stop', True), ('start', 320)])
        self.assertEqual(lan.read(self.config)['allowed_peers'], [lan.PEER])
        self.assertEqual(result['session_id'], 'b' * 32)
        restored = lan.rollback(self.live, result['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertEqual(restored['session_id'], 'c' * 32)
        self.assertTrue(all(call[1] is True for call in self.live.manage.calls if call[0] == 'normal_stop'))

    def test_stale_inspection_never_stops_or_changes_config(self):
        with self.assertRaisesRegex(RuntimeError, 'inspection_owner_or_config_changed'):
            lan.switch(self.live, 'f' * 32, lan.digest(self.original), explicit_controlled_model_release=True)
        self.assertEqual(self.live.manage.calls, [])
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_failed_start_retains_owned_candidate_and_can_restore(self):
        self.live.manage.fail_start = True
        with self.assertRaisesRegex(RuntimeError, 'isolated_start_failure'):
            self.handoff()
        receipt = next((self.work / 'transactions').glob('*/transaction.json'))
        value = lan.read(receipt)
        self.assertEqual(value['candidate_record']['session_id'], 'b' * 32)
        result = lan.rollback(self.live, value['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(result['status'], 'ROLLED_BACK_LOCAL_READY')
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_rollback_refuses_foreign_owner_and_changed_configuration(self):
        result = self.handoff()
        record = copy.deepcopy(self.live.manage.record)
        self.live.manage.record['session_id'] = 'e' * 32
        with self.assertRaisesRegex(RuntimeError, 'different_or_unrecorded_owner'):
            lan.rollback(self.live, result['transaction_id'], 'e' * 32, explicit_controlled_model_release=True)
        self.live.manage.record = record
        self.config.write_bytes(b'{"unrelated":true}')
        with self.assertRaisesRegex(RuntimeError, 'changed_configuration'):
            lan.rollback(self.live, result['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(len(self.live.closed), 1)

    def test_release_is_never_the_default_authorization(self):
        with self.assertRaisesRegex(RuntimeError, 'explicit_controlled_model_release_authorization_required'):
            lan.switch(self.live, 'a' * 32, lan.digest(self.original))
        with self.assertRaisesRegex(RuntimeError, 'explicit_controlled_model_release_authorization_required'):
            lan.rollback(self.live, 'f' * 32, 'a' * 32)
        self.assertEqual(self.live.manage.calls, [])
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_switch_refuses_model_not_owned_by_current_session(self):
        self.live.owns_model = False
        with self.assertRaisesRegex(RuntimeError, 'current_session_must_own_fixed_model'):
            self.handoff()
        self.assertEqual(self.live.manage.calls, [])
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_release_refuses_busy_changed_daemon_foreign_model_or_context(self):
        def busy(live):
            live.busy = True
        def daemon(live):
            live.manage.state_daemon_override = dict(live.fixed_daemon, pid=999)
        def foreign(live):
            live.model_rows[0]['name'] = 'foreign-model'
        def context(live):
            live.model_rows[0]['context_length'] = 4096
        for configure, error in ((busy, 'current_model_service_must_be_idle'),
                                 (daemon, 'release_fixed_daemon_owner_changed'),
                                 (foreign, 'fake_foreign_model'),
                                 (context, 'original_27b_2048_residency_required')):
            with self.subTest(case=configure.__name__):
                self.live = FakeLive()
                configure(self.live)
                with self.assertRaisesRegex(RuntimeError, error):
                    self.handoff()
                self.assertEqual(self.live.manage.calls, [])
                self.assertEqual(self.config.read_bytes(), self.original)

    def test_missing_release_receipt_refuses_config_write_and_start(self):
        self.live.manage.missing_release_receipt = True
        with self.assertRaisesRegex(RuntimeError, 'explicit_owned_model_release_receipt_required'):
            self.handoff()
        self.assertEqual(self.live.manage.calls, [('normal_stop', True)])
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_claimed_release_without_empty_residency_never_starts(self):
        self.live.manage.leave_model_resident = True
        with self.assertRaisesRegex(RuntimeError, 'model_still_resident_tts_first_start_refused'):
            self.handoff()
        self.assertEqual(self.live.manage.calls, [('normal_stop', True)])
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_dead_candidate_with_resident_model_is_frozen_for_ownership_repair(self):
        self.live.manage.fail_start_after_model_load = True
        with self.assertRaisesRegex(RuntimeError, 'isolated_post_model_start_failure'):
            self.handoff()
        receipt = next((self.work / 'transactions').glob('*/transaction.json'))
        value = lan.read(receipt)
        lan_config = self.config.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'model_still_resident_tts_first_start_refused'):
            lan.rollback(self.live, value['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(self.config.read_bytes(), lan_config)
        self.assertEqual(self.live.manage.calls, [('normal_stop', True), ('start', 320)])
        self.assertEqual(len(self.live.model_rows), 1)

    def test_rollback_cannot_release_a_live_unowned_model(self):
        result = self.handoff()
        self.live.owns_model = False
        lan_config = self.config.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'rollback_live_session_does_not_own_resident_model'):
            lan.rollback(self.live, result['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(self.config.read_bytes(), lan_config)
        self.assertEqual(len(self.live.closed), 1)

    def test_rollback_starting_candidate_without_resident_model_uses_normal_cleanup(self):
        self.live.manage.fail_start = True
        with self.assertRaisesRegex(RuntimeError, 'isolated_start_failure'):
            self.handoff()
        receipt = next((self.work / 'transactions').glob('*/transaction.json'))
        value = lan.read(receipt)
        self.live.manage.alive = True
        self.live.manage.state_status = 'STARTING'
        result = lan.rollback(self.live, value['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(result['status'], 'ROLLED_BACK_LOCAL_READY')
        self.assertEqual(self.live.manage.calls, [('normal_stop', True), ('start', 320),
                                                ('normal_stop', False), ('start', 320)])
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_legacy_transaction_cannot_be_resumed_by_new_release_flow(self):
        result = self.handoff()
        receipt = self.work / 'transactions' / result['transaction_id'] / 'transaction.json'
        value = lan.read(receipt)
        value.pop('maintenance_contract')
        value.pop('explicit_controlled_model_release')
        lan.write(receipt, value)
        with self.assertRaisesRegex(RuntimeError, 'legacy_transaction_frozen_requires_new_authorization'):
            lan.rollback(self.live, result['transaction_id'], 'b' * 32, explicit_controlled_model_release=True)
        self.assertEqual(len(self.live.closed), 1)

    def test_board_probe_disables_remote_bytecode_writes(self):
        handoff = self.handoff()
        ssh_calls = []
        def fake_ssh(command, script, timeout):
            ssh_calls.append((command, script, timeout))
            return json.dumps(dict(status='PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS',
                              board_boot_id=lan.BOARD_BOOT, audio_device_opened=False,
                              business_database_opened=False, board_file_modified=False))
        with patch.dict(sys.modules, {'board_ssh': SimpleNamespace(ssh=fake_ssh)}), \
                patch.object(lan.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as firewall_check, \
                patch.object(lan, 'board_script', return_value='# isolated public script'):
            result = lan.probe_board(self.live, handoff['transaction_id'], 'b' * 32)
        self.assertEqual(firewall_check.call_count, 1)
        self.assertEqual(firewall_check.call_args.kwargs['timeout'], 600)
        self.assertEqual(firewall_check.call_args.args[0][-4:], ['-Action', 'Check', '-ExpectedSession', 'b' * 32])
        self.assertEqual(len(ssh_calls), 1)
        self.assertEqual(ssh_calls[0][0], 'python3 -B -')
        self.assertFalse(result['audio_played'])

    def test_firewall_check_timeout_does_not_contact_board_or_advance_transaction(self):
        handoff = self.handoff()
        receipt = self.work / 'transactions' / handoff['transaction_id'] / 'transaction.json'
        before = receipt.read_bytes()
        ssh_calls = []
        def fake_ssh(*args, **kwargs):
            ssh_calls.append((args, kwargs))
            raise AssertionError('Board must not be contacted after firewall Check timeout')
        with patch.dict(sys.modules, {'board_ssh': SimpleNamespace(ssh=fake_ssh)}), \
                patch.object(lan.subprocess, 'run', side_effect=lan.subprocess.TimeoutExpired('powershell.exe', 600)) as firewall_check:
            with self.assertRaises(lan.subprocess.TimeoutExpired):
                lan.probe_board(self.live, handoff['transaction_id'], 'b' * 32)
        self.assertEqual(firewall_check.call_args.kwargs['timeout'], 600)
        self.assertEqual(ssh_calls, [])
        self.assertEqual(receipt.read_bytes(), before)


class FakeHttpModels:
    def __init__(self):
        self.calls = 0
        self.clock = time.monotonic

    def health(self):
        return healthy()

    def handle(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('Denied peer must never enter inference')


class WireAndHttpTests(unittest.TestCase):
    def test_real_local_health_exception_does_not_allow_local_post(self):
        models = FakeHttpModels()
        server = make_server((lan.LOCAL, 0), models, allowed_peers=[lan.PEER], local_health=True)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        thread.start()
        try:
            def call(method, path, body=None):
                connection = http.client.HTTPConnection(lan.LOCAL, server.server_port, timeout=2)
                try:
                    connection.request(method, path, body, {'Content-Type': 'application/json'})
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()
            self.assertEqual(call('GET', '/health')[0], 200)
            for path in ('/v1/inference/llm', '/v1/inference/tts', '/v1/inference/warmup'):
                status, value = call('POST', path, b'{}')
                self.assertEqual(status, 403)
                self.assertEqual(value['error']['code'], 'peer_denied')
            self.assertEqual(models.calls, 0)
        finally:
            server.shutdown()
            thread.join(2)
            server.server_close()

    def test_exact_wire_owner_and_pcm_digest_are_enforced(self):
        owner = Owner('public-id', 'public-boot', 'public-session', 1)
        audio = audio_payload(b'\x01\x00' * 12)
        payload = dict(protocol_version=1, **owner.as_dict(), ok=True, result={'audio': audio})
        validate_response(payload, owner, 'tts')
        self.assertEqual(decode_audio(audio)[0], b'\x01\x00' * 12)
        with self.assertRaises(WireError):
            validate_response(dict(payload, generation=2), owner, 'tts')
        with self.assertRaises(WireError):
            decode_audio(dict(audio, sha256='0' * 64))

    def test_prepared_board_probe_uses_production_wire_and_only_reads_boot(self):
        opened = []
        calls = []
        namespace = {'__name__': 'isolated_board_probe'}
        class Response:
            status = 200
            def __init__(self, value):
                self.value = value
            def read(self, limit):
                return json.dumps(self.value).encode()
        class Connection:
            def __init__(self, host, port, timeout):
                if (host, port) != (lan.LAN, 8797):
                    raise AssertionError('Unexpected destination')
            def request(self, method, path, raw, headers):
                self.path = path
                self.body = json.loads(raw) if raw else None
                calls.append((method, path))
            def getresponse(self):
                if self.path == '/health':
                    return Response(healthy())
                wire = sys.modules['common.model_inference_wire']
                owner = wire.Owner.from_dict(self.body)
                result = {'text': '公开验证成功。'} if self.path.endswith('/llm') else {'audio': wire.audio_payload(b'\x01\x00' * 24)}
                return Response(wire.make_response(owner, result=result))
            def close(self):
                pass
        def boot_only(path, **kwargs):
            opened.append(path)
            if path != '/proc/sys/kernel/random/boot_id':
                raise AssertionError('Unexpected board file access')
            return io.StringIO(lan.BOARD_BOOT)
        with patch.dict(sys.modules), patch('http.client.HTTPConnection', Connection), patch('builtins.open', boot_only):
            exec(compile(lan.board_script(), '<prepared-board-probe>', 'exec'), namespace)
            report = namespace['main']()
        self.assertEqual(report['status'], 'PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS')
        self.assertEqual(report['tts']['samples'], 24)
        self.assertFalse(report['response_text_or_pcm_archived'])
        self.assertEqual(opened, ['/proc/sys/kernel/random/boot_id'])
        self.assertEqual(calls, [('GET', '/health'), ('POST', '/v1/inference/llm'),
                                 ('POST', '/v1/inference/tts'), ('GET', '/health')])


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
