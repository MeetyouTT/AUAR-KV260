"""Public synthetic metadata only. No board/process/network/model/store action."""
import ast
import copy
import graphlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))
import recovery_rules as rules
import boot_recovery as runtime
import manage_installation as install

BOOT = '11111111-2222-4333-8444-555555555555'
PREVIOUS = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
OWNER = dict(pid=701, birth_ticks='12345', command_sha256='1' * 64)


def platform_fixture(app=rules.APP):
    return dict(firmware=app + '.bit.bin', fpga_state='operating',
                vart='firmware: /lib/firmware/xilinx/' + app + '/' + app + '.xclbin\n',
                fdt_sha256='2' * 64, overlays=[dict(name=app + '_image_77', status='applied')],
                render=[dict(name='renderD128', device='/sys/devices/platform/amba/test-zocl')],
                zocl_links=['/sys/devices/platform/amba/test-zocl', '/sys/devices/platform/amba/test-zocl/dpu'],
                unexpected_zocl_links=[])


def final_fixture():
    return rules.encoded(dict(schema='aura-native-protection-checkpoint-2',
                              scope='final_quiescent_before_native_owner_close',
                              seed=dict(purpose='final_quiescent_business_checkpoint', checkpoint_kind=1,
                                        boot_id=PREVIOUS, source_pid=OWNER['pid'], source_birth_ticks=int(OWNER['birth_ticks']), fenced=0)))


def report_fixture():
    return dict(boot_id=BOOT, manifest_sha256=rules.MANIFEST_SHA, identity_stop_passed=True,
                ARM_sent=False, COMMIT_sent=False, BIND_sent=False, REFERENCE_sent=False,
                after_stop=dict(flags=0, lease_left_ms=0))


def job_fixture():
    return dict(InvocationID='a' * 32, MainPID='0', ActiveState='active', SubState='exited', Job='',
                ExecMainCode='1', ExecMainStatus='0', Result='success', ExecMainPID='800',
                ExecMainStartTimestampMonotonic='100', ExecMainExitTimestampMonotonic='200')


def table(app):
    other = rules.BENCHMARK if app == rules.APP else rules.APP
    return ('Accelerator Accel_type Base Base_type #slots(PL+AIE) Active_slot\n'
            + app + ' XRT_FLAT ' + app + ' XRT_FLAT (0+0) 0,\n'
            + other + ' XRT_FLAT ' + other + ' XRT_FLAT (0+0) -1\n').encode()


def safe_scan():
    return dict(complete=True, owners=[], unreadable=[])


def local_create(path, raw):
    # All test writes are isolated under the task-local temporary directory.
    with Path(path).open('xb') as stream:
        stream.write(raw)


def checked_cleanup(temporary):
    target = Path(temporary.name).resolve()
    allowed = (HERE / 'test_work').resolve()
    if target.parent != allowed or Path(temporary.name).is_symlink():
        raise RuntimeError('Test cleanup target escaped the task-local test directory')
    temporary.cleanup()


class RulesTests(unittest.TestCase):
    def test_original_bootstrap_must_match_this_gate_final_and_source_owner(self):
        gate = dict(boot_id=BOOT, contract_sha256='7' * 64, checkpoint_sha256='8' * 64,
                    predecessor=dict(boot_id=PREVIOUS, camera_owner=OWNER))
        handoff = dict(mode='native_new_kernel_boot', seed_sha256='8' * 64, current_boot=BOOT, source_boot=PREVIOUS,
                       source_pid=OWNER['pid'], source_birth_ticks=int(OWNER['birth_ticks']))
        rules.verify_bootstrap_handoff(handoff, gate, BOOT, '7' * 64)
        for key, value in (('seed_sha256', '9' * 64), ('source_pid', 999), ('current_boot', PREVIOUS), ('source_boot', BOOT)):
            changed = dict(handoff, **{key: value})
            with self.subTest(key=key), self.assertRaises(rules.Hold):
                rules.verify_bootstrap_handoff(changed, gate, BOOT, '7' * 64)

    def test_saved_original_package_reply_parses(self):
        raw = (HERE / 'evidence/original_list_package.txt').read_bytes()
        self.assertEqual(rules.loaded_app(raw), rules.BENCHMARK)

    def test_wide_reply_parses_with_dynamic_order(self):
        self.assertEqual(rules.loaded_app(table(rules.APP)), rules.APP)

    def test_package_ambiguity_or_unknown_slot_is_refused(self):
        for raw in (table(rules.APP).replace(b'-1', b'0,'), table(rules.APP).replace(b'0,', b'1,'), b'Ok\n'):
            with self.subTest(raw=raw), self.assertRaises(rules.Hold):
                rules.loaded_app(raw)

    def test_single_returncode_is_insufficient(self):
        for stdout, stderr in ((b'0\n', b''), (rules.REPLIES['load'], b'warning\n'), (b'', b'')):
            with self.subTest(stdout=stdout), self.assertRaises(rules.Hold):
                rules.verify_job(job_fixture(), 'a' * 32, stdout, stderr, 'load')

    def test_exact_original_remove_and_load_replies(self):
        for action in ('remove', 'load'):
            rules.verify_job(job_fixture(), 'a' * 32, rules.REPLIES[action], b'', action)

    def test_job_replaced_or_pending_or_failed_is_hold(self):
        for key, value in (('InvocationID', 'b' * 32), ('MainPID', '800'), ('Job', '19'),
                           ('ExecMainStatus', '1'), ('Result', 'exit-code'), ('ExecMainExitTimestampMonotonic', '0')):
            current = job_fixture()
            current[key] = value
            with self.subTest(key=key), self.assertRaises(rules.Hold):
                rules.verify_job(current, 'a' * 32, rules.REPLIES['remove'], b'', 'remove')

    def test_dynamic_overlay_suffix_and_unchanged_fdt_accepted(self):
        current = platform_fixture()
        for suffix in ('1', '9001'):
            current['overlays'][0]['name'] = rules.APP + '_image_' + suffix
            rules.verify_platform(current, rules.APP)

    def test_each_platform_pairing_boundary(self):
        mutations = [lambda v: v.update(vart='firmware: stale\n'),
                     lambda v: v.update(firmware=rules.BENCHMARK + '.bit.bin'),
                     lambda v: v['overlays'][0].update(status='unapplied'),
                     lambda v: v['overlays'][0].update(name='unrelated_image_1'),
                     lambda v: v['zocl_links'].append('/sys/devices/unrelated'),
                     lambda v: v.update(zocl_links=['/sys/devices/platform/amba/test-zocl/dpu']),
                     lambda v: v['render'].append(copy.deepcopy(v['render'][0])),
                     lambda v: v['unexpected_zocl_links'].append('/sys/unknown')]
        for index, mutation in enumerate(mutations):
            current = platform_fixture()
            mutation(current)
            with self.subTest(index=index), self.assertRaises(rules.Hold):
                rules.verify_platform(current, rules.APP)

    def test_unload_requires_actual_teardown(self):
        value = platform_fixture()
        with self.assertRaises(rules.Hold):
            rules.verify_unloaded(value)
        value.update(firmware=None, overlays=[], render=[], zocl_links=[])
        rules.verify_unloaded(value)

    def test_owner_or_unreadable_process_blocks_dfx(self):
        for value in (dict(complete=True, owners=[OWNER], unreadable=[]), dict(complete=False, owners=[], unreadable=[19])):
            with self.subTest(value=value), self.assertRaises(rules.Hold):
                rules.require_no_owners(value)

    def test_original_idstop_proves_no_arm_bind_or_reference(self):
        rules.verify_idstop(report_fixture(), BOOT, rules.MANIFEST_SHA)
        for key in ('ARM_sent', 'COMMIT_sent', 'BIND_sent', 'REFERENCE_sent'):
            report = report_fixture()
            report[key] = True
            with self.subTest(key=key), self.assertRaises(rules.Hold):
                rules.verify_idstop(report, BOOT, rules.MANIFEST_SHA)

    def test_axis_output_or_lease_not_disabled_blocks_ready(self):
        for key in ('flags', 'lease_left_ms'):
            report = report_fixture()
            report['after_stop'][key] = 1
            with self.subTest(key=key), self.assertRaises(rules.Hold):
                rules.verify_idstop(report, BOOT, rules.MANIFEST_SHA)

    def test_final_pointer_requires_latest_owner(self):
        predecessor = dict(boot_id=PREVIOUS, camera_owner=OWNER)
        rules.verify_final_pointer(final_fixture(), False, predecessor)
        newer = dict(predecessor, camera_owner=dict(OWNER, birth_ticks='999'))
        with self.assertRaises(rules.Hold):
            rules.verify_final_pointer(final_fixture(), False, newer)

    def test_consumed_final_is_never_replayed(self):
        with self.assertRaisesRegex(rules.Hold, 'CONSUMED_FINAL_POINTER'):
            rules.verify_final_pointer(final_fixture(), True, dict(boot_id=PREVIOUS, camera_owner=OWNER))

    def test_known_c6c8_final_is_explicitly_forbidden(self):
        with patch.object(rules, 'digest', return_value=rules.FORBIDDEN_OLD_FINAL):
            with self.assertRaisesRegex(rules.Hold, 'C6C8'):
                rules.verify_final_pointer(b'synthetic-only', False, {})

    def test_partial_or_fenced_final_is_refused(self):
        for mutation in (lambda d: d['seed'].update(fenced=1), lambda d: d.update(scope='periodic')):
            doc = json.loads(final_fixture())
            mutation(doc)
            with self.assertRaises(rules.Hold):
                rules.verify_final_pointer(rules.encoded(doc), False, dict(boot_id=PREVIOUS, camera_owner=OWNER))

    def test_binding_keeps_all_historical_pins_and_policy(self):
        sources = {'/public/old-run-1/config.json': '3' * 64, '/public/camera.py': '4' * 64}
        selected = dict(board_boot_id=PREVIOUS, camera_pid=9, camera_start_ticks='99', camera_cmdline_sha256='5' * 64,
                        camera_config='/public/old-run-1/config.json', source_sha256=sources,
                        backend='DPU_SFACE_INT8', result_ttl_ms=3000, dimension=128,
                        test_policy=dict(threshold=.5, margin=.1))
        fresh = rules.make_binding(selected, BOOT, OWNER, dict(path='/public/new-run/config.json', sha256='6' * 64), sources)
        self.assertEqual(len(fresh['source_sha256']), 3)
        self.assertEqual(fresh['test_policy'], selected['test_policy'])
        for path, pin in sources.items():
            self.assertEqual(fresh['source_sha256'][path], pin)
        self.assertEqual(selected['camera_pid'], 9)

    def test_changed_source_binding_is_not_reblessed(self):
        selected = dict(source_sha256={'/public/camera.py': '4' * 64})
        with self.assertRaisesRegex(rules.Hold, 'SOURCE_MAP_CHANGED'):
            rules.make_binding(selected, BOOT, OWNER, dict(path='/public/new.json', sha256='5' * 64), {'/public/camera.py': '6' * 64})

    def test_conflicting_existing_run_pin_is_refused(self):
        sources = {'/public/new.json': '4' * 64}
        with self.assertRaises(rules.Hold):
            rules.make_binding(dict(source_sha256=sources), BOOT, OWNER, dict(path='/public/new.json', sha256='5' * 64), sources)

    def test_only_selected_spec_and_existing_ui_pin_change(self):
        pins = {'file' + str(i) + '.py': '3' * 64 for i in range(379)}
        pins['config/board_avatar_gtk.json'] = '4' * 64
        startup = dict(runtime='/public/current', component_sha256=pins, gui_sha256='5' * 64, latest_identity='preserve')
        ui = dict(board_business=dict(face_readback=dict(path='/old', sha256='6' * 64), identity_fix='latest'), gtk_optimization='keep', pan='keep')
        ui_raw, startup_raw = rules.config_patch(startup, ui, dict(path='/new', sha256='7' * 64))
        updated, new_ui = json.loads(startup_raw), json.loads(ui_raw)
        self.assertEqual([k for k in pins if updated['component_sha256'][k] != pins[k]], ['config/board_avatar_gtk.json'])
        self.assertEqual(new_ui['board_business']['identity_fix'], 'latest')
        self.assertEqual(new_ui['gtk_optimization'], 'keep')
        self.assertEqual({k: v for k, v in updated.items() if k != 'component_sha256'}, {k: v for k, v in startup.items() if k != 'component_sha256'})


def gui_state(sequence=1):
    return dict(sequence=sequence, ui_page='main', phase='IDLE', playing=False,
                character_pair=dict(state='READY', production_selected=True, fallback_allowed=False),
                avatar_display=dict(visible=True, frames=sequence * 16),
                handsfree_dialogue=dict(enabled=False, microphone_open=False, state='PAUSED'),
                manual_pan=dict(state='FAULT', automatic_following=False, readback=None, pulse_us=None),
                board_business=dict(started=True, closed=False, writer=dict(held=True), clock=dict(anchored=True, same_boot=True)),
                runtime_faults=dict(count=0))


class ReadyTests(unittest.TestCase):
    def test_ready_requires_advancing_avatar_and_locked_axis(self):
        rules.verify_ready(rules.gui_projection(gui_state(1)), rules.gui_projection(gui_state(2)), False)
        for mutation in (lambda v: v['manual_pan'].update(automatic_following=True),
                         lambda v: v['manual_pan'].update(state='READY', readback=dict(flags=0)),
                         lambda v: v['avatar_display'].update(frames=16),
                         lambda v: v['board_business']['clock'].update(anchored=False),
                         lambda v: v['handsfree_dialogue'].update(microphone_open=True)):
            later = gui_state(2)
            mutation(later)
            with self.assertRaises(rules.Hold):
                rules.verify_ready(rules.gui_projection(gui_state(1)), rules.gui_projection(later), False)

    def test_api_projection_cannot_export_private_text_ids_or_templates(self):
        state = gui_state()
        state.update(transcript='DO_NOT_EXPORT_TEXT', name='DO_NOT_EXPORT_NAME', identity_id='DO_NOT_EXPORT_ID', embedding=[1., 2.])
        state['board_business']['identity'] = dict(person_id='DO_NOT_EXPORT_ID')
        projected = json.dumps(rules.gui_projection(state))
        self.assertNotIn('DO_NOT_EXPORT', projected)
        self.assertNotIn('embedding', projected)

    def test_saved_listening_preference_is_preserved_without_writing_it(self):
        first, last = gui_state(1), gui_state(2)
        for value in (first, last):
            value['handsfree_dialogue'].update(enabled=True, microphone_open=True, state='WAITING_SPEECH')
        rules.verify_ready(rules.gui_projection(first), rules.gui_projection(last), True)
        with self.assertRaises(rules.Hold):
            rules.verify_ready(rules.gui_projection(first), rules.gui_projection(last), False)


class FakeRecovery(runtime.Recovery):
    def __init__(self, temp, existing_wide=False):
        self.tx, self.boot, self.contract_sha = Path(temp), BOOT, '7' * 64
        self.contract = dict(installed_boot_id=PREVIOUS, startup_path='/public/startup.json')
        self.events, self.present_owner, self.unknown_load = [], False, False
        self.plat = platform_fixture(rules.APP if existing_wide else rules.BENCHMARK)
        self.startup_raw = b'public synthetic startup'
        self.checkpoint = final_fixture()
        self.source_changed_after = None
        self.idstop_bad = False

    def source_snapshot(self):
        if self.source_changed_after and self.source_changed_after in self.events:
            raise rules.Hold('STARTUP_CHANGED_RESEAL_REQUIRED')
        return dict(startup_raw=self.startup_raw, active=dict(predecessor=dict(boot_id=PREVIOUS, camera_owner=OWNER)))

    def original_release(self):
        self.events.append('verify_original_release')

    def quiet(self):
        rules.require(not self.present_owner, 'HARDWARE_OWNER_PRESENT')

    def daemon_owner(self):
        return dict(OWNER, executable_sha256=rules.DAEMON_SHA)

    def once(self, action, argv, allow_submit=True):
        intent_path = self.tx / (action + '-intent.json')
        existing = intent_path.exists()
        if not existing:
            rules.require(allow_submit, 'NO_EXISTING_JOB_TO_OBSERVE')
            local_create(intent_path, rules.encoded({'synthetic_only': True}))
        self.events.append('observe-' + action if existing else action)
        self.last_argv = argv
        if action == 'list':
            path = self.tx / 'list.stdout.raw'
            if not path.exists():
                local_create(path, table(rules.APP if self.plat['firmware'] == rules.APP + '.bit.bin' else rules.BENCHMARK))
            return rules.loaded_app(path.read_bytes()), job_fixture()
        if action == 'remove' and not existing:
            self.plat.update(firmware=None, overlays=[], render=[], zocl_links=[])
        if action == 'load':
            if self.unknown_load:
                raise rules.Hold('UNKNOWN_OR_PENDING_OS_JOB_NO_RETRY')
            if not existing:
                self.plat = platform_fixture()
        if action == 'idstop' and not existing:
            report = report_fixture()
            if self.idstop_bad:
                report['after_stop']['flags'] = 1
            local_create(self.tx / 'id-stop.json', rules.encoded(report))
            local_create(self.tx / 'idstop.stdout.raw', rules.encoded(dict(identity_stop_passed=True, motion_tested=False, report=str(self.tx / 'id-stop.json'))))
        return None, job_fixture()

    def read(self, path, limit=67108864):
        if Path(path) == runtime.CHECKPOINT:
            return self.checkpoint
        if str(path) == self.contract['startup_path']:
            return self.startup_raw
        return Path(path).read_bytes()


class PrepareTests(unittest.TestCase):
    def test_camera_gate_records_exact_final_without_consuming_or_rewriting_it(self):
        self.r.prepare()
        before = self.r.checkpoint
        properties = dict(Restart='no', KillMode='process', SendSIGKILL='no', TimeoutStopUSec='infinity')
        with patch.object(runtime, 'unit', return_value=properties):
            result = self.r.camera_check()
        gate = json.loads((self.r.tx / 'current-camera-gate.json').read_bytes())
        self.assertEqual(gate['checkpoint_sha256'], rules.digest(before))
        self.assertEqual(self.r.checkpoint, before)
        self.assertFalse(result['checkpoint_seed_marker_modified'])

    def test_camera_gate_refuses_a_consumed_pointer_before_original_start(self):
        self.r.prepare()
        properties = dict(Restart='no', KillMode='process', SendSIGKILL='no', TimeoutStopUSec='infinity')
        original_lexists = os.path.lexists
        def consumed(path):
            if str(path).startswith(str(runtime.CHECKPOINT) + '.native-consumed-'):
                return True
            return original_lexists(path)
        with patch.object(runtime, 'unit', return_value=properties), patch.object(runtime.os.path, 'lexists', consumed):
            with self.assertRaisesRegex(rules.Hold, 'CONSUMED_FINAL_POINTER'):
                self.r.camera_check()
        self.assertFalse((self.r.tx / 'current-camera-gate.json').exists())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        self.r = FakeRecovery(self.temp.name)
        self.patches = [patch.object(runtime, 'regular', self.r.read), patch.object(runtime, 'create', local_create),
                        patch.object(runtime, 'platform_metadata', lambda: copy.deepcopy(self.r.plat)),
                        patch.object(runtime, 'owner_scan', lambda **kw: safe_scan())]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        checked_cleanup(self.temp)

    def test_actual_sequential_start_order_no_camera_or_motion_start(self):
        result = self.r.prepare()
        self.assertEqual(result['status'], 'ORIGINAL_WIDE_READY_IDSTOP_ONLY')
        self.assertEqual([v for v in self.r.events if v != 'verify_original_release'], ['list', 'remove', 'load', 'idstop'])
        self.assertNotIn('start', self.r.last_argv)
        self.assertEqual(self.r.last_argv[self.r.last_argv.index('--confirmation') + 1], 'ID_STOP_ONLY')
        self.assertFalse(result['reference_initialized'])
        self.assertFalse(result['follow_started'])

    def test_already_wide_skips_remove_load_but_uses_original_stop(self):
        self.r.plat = platform_fixture()
        self.r.prepare()
        self.assertEqual([v for v in self.r.events if v != 'verify_original_release'], ['list', 'idstop'])

    def test_successful_reentry_checks_receipt_and_never_replays_dfx(self):
        self.r.prepare()
        before = self.r.events[:]
        result = self.r.prepare()
        self.assertEqual(result['status'], 'ALREADY_PREPARED_NO_DFX_RESUBMISSION')
        self.assertEqual(self.r.events, before + ['verify_original_release'])

    def test_existing_hardware_owner_blocks_before_any_original_call(self):
        self.r.present_owner = True
        with self.assertRaises(rules.Hold):
            self.r.prepare()
        self.assertNotIn('list', self.r.events)

    def test_unknown_load_never_runs_idstop_or_publishes_prepared(self):
        self.r.unknown_load = True
        with self.assertRaisesRegex(rules.Hold, 'NO_RETRY'):
            self.r.prepare()
        self.assertNotIn('idstop', self.r.events)
        self.assertFalse((self.r.tx / 'prepared.json').exists())

    def test_explicit_resume_observes_finished_load_without_replaying_remove_load(self):
        self.r.unknown_load = True
        with self.assertRaises(rules.Hold):
            self.r.prepare()
        self.r.unknown_load = False
        self.r.plat = platform_fixture()  # Same original OS-owned load completed later.
        result = self.r.prepare()
        self.assertEqual(result['status'], 'ORIGINAL_WIDE_READY_IDSTOP_ONLY')
        self.assertEqual(self.r.events.count('remove'), 1)
        self.assertEqual(self.r.events.count('load'), 1)
        self.assertEqual(self.r.events.count('observe-load'), 1)
        self.assertEqual(self.r.events.count('idstop'), 1)

    def test_source_change_after_remove_aborts_before_load(self):
        self.r.source_changed_after = 'remove'
        with self.assertRaisesRegex(rules.Hold, 'STARTUP_CHANGED'):
            self.r.prepare()
        self.assertNotIn('load', self.r.events)
        self.assertFalse((self.r.tx / 'prepared.json').exists())

    def test_unconfirmed_stop_prevents_camera_start_gate(self):
        self.r.idstop_bad = True
        with self.assertRaises(rules.Hold):
            self.r.prepare()
        self.assertFalse((self.r.tx / 'prepared.json').exists())

    def test_install_boot_refuses_automatic_current_owner_recovery(self):
        self.r.contract['installed_boot_id'] = BOOT
        with self.assertRaisesRegex(rules.Hold, 'MANUAL_MAIN_AXIS'):
            self.r.prepare()
        self.assertNotIn('list', self.r.events)

    def test_wrong_dynamic_vart_prevents_remove(self):
        self.r.plat['vart'] = 'firmware: unrelated\n'
        with self.assertRaises(rules.Hold):
            self.r.prepare()
        self.assertNotIn('remove', self.r.events)


class OnceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        self.r = FakeRecovery(self.temp.name)
        self.state = {'LoadState': 'not-found'}
        self.submissions = 0
        self.order = []
        self.patches = [patch.object(runtime, 'regular', self.r.read), patch.object(runtime, 'create', self.create),
                        patch.object(runtime, 'unit', lambda name: copy.deepcopy(self.state))]
        for item in self.patches:
            item.start()

    def create(self, path, raw):
        self.order.append(Path(path).name)
        local_create(path, raw)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        checked_cleanup(self.temp)

    def dispatch_complete(self, argv, timeout):
        self.submissions += 1
        self.order.append('dispatch')
        self.state = job_fixture()
        (self.r.tx / 'remove.stdout.raw').write_bytes(rules.REPLIES['remove'])
        return subprocess.CompletedProcess(argv, 0, b'unit submitted', b'')

    def invoke(self):
        return runtime.Recovery.once(self.r, 'remove', [rules.CLIENT, '-remove', '0'])

    def test_durable_intent_precedes_dispatch_and_success_reentry_only_observes(self):
        with patch.object(runtime, 'command', self.dispatch_complete):
            self.invoke()
            self.invoke()
        self.assertEqual(self.submissions, 1)
        self.assertLess(self.order.index('remove-intent.json'), self.order.index('dispatch'))

    def test_unknown_submission_is_durable_and_never_resent(self):
        def uncertain(argv, timeout):
            self.submissions += 1
            self.state = dict(LoadState='loaded', ActiveState='active', SubState='running', InvocationID='a' * 32)
            raise subprocess.TimeoutExpired(argv, timeout)
        with patch.object(runtime, 'command', uncertain), patch.object(runtime.time, 'monotonic', side_effect=[0, 26, 30, 56]):
            for _ in range(2):
                with self.assertRaisesRegex(rules.Hold, 'NO_RETRY'):
                    self.invoke()
        self.assertEqual(self.submissions, 1)
        self.assertTrue((self.r.tx / 'remove-intent.json').exists())

    def test_existing_unexplained_job_never_dispatches(self):
        self.state = job_fixture()
        with patch.object(runtime, 'command') as dispatch:
            with self.assertRaisesRegex(rules.Hold, 'UNEXPLAINED'):
                self.invoke()
            dispatch.assert_not_called()

    def test_readonly_observer_cannot_create_or_submit_missing_job(self):
        with patch.object(runtime, 'command') as dispatch:
            with self.assertRaisesRegex(rules.Hold, 'NO_EXISTING_JOB'):
                runtime.Recovery.once(self.r, 'remove', [rules.CLIENT, '-remove', '0'], allow_submit=False)
            dispatch.assert_not_called()
        self.assertFalse((self.r.tx / 'remove-intent.json').exists())

    def test_replaced_invocation_is_not_accepted(self):
        with patch.object(runtime, 'command', self.dispatch_complete):
            self.invoke()
        self.state['InvocationID'] = 'b' * 32
        with self.assertRaisesRegex(rules.Hold, 'OS_JOB_REPLACED'):
            self.invoke()
        self.assertEqual(self.submissions, 1)

    def test_daemon_owner_change_cannot_inherit_old_submission(self):
        with patch.object(runtime, 'command', self.dispatch_complete):
            self.invoke()
        self.r.daemon_owner = lambda: dict(OWNER, birth_ticks='999', executable_sha256=rules.DAEMON_SHA)
        with self.assertRaisesRegex(rules.Hold, 'INTENT_CONTEXT_CHANGED'):
            self.invoke()
        self.assertEqual(self.submissions, 1)


class PackagingTests(unittest.TestCase):
    def test_target_unit_verify_uses_retained_original_fragments_without_service_action(self):
        complete = subprocess.CompletedProcess([], 0, b'', b'')
        with patch.object(install, 'unit', return_value={'FragmentPath': '/etc/systemd/system/original.service'}), patch.object(install.subprocess, 'run', return_value=complete) as run:
            install.verify_unit_graph()
        argv = run.call_args.args[0]
        self.assertEqual(argv[:3], ['systemd-analyze', 'verify', '--man=no'])
        self.assertIn('/etc/systemd/system/original.service', argv)
        self.assertEqual(run.call_count, 1)

    def test_failed_target_unit_verify_prevents_activation_stage(self):
        failed = subprocess.CompletedProcess([], 1, b'', b'cycle or unavailable tool')
        with patch.object(install, 'unit', return_value={'FragmentPath': '/etc/systemd/system/original.service'}), patch.object(install.subprocess, 'run', return_value=failed):
            with self.assertRaisesRegex(rules.Hold, 'NO_ACTIVATION'):
                install.verify_unit_graph()

    def test_python39_candidate_syntax(self):
        for name in install.PYTHON_FILES:
            ast.parse((HERE / 'candidate' / name).read_text(), feature_version=(3, 9))

    def test_cpu_adapters_are_referenced_with_the_actual_saved_reviewed_bytes(self):
        reference = json.loads((HERE / 'candidate/cpu_adapters.reference.json').read_bytes())
        for value in reference['adapters'].values():
            path = HERE.parent / 'cpu_optimization_20261102/camera' / value['filename']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), value['sha256'])
        self.assertFalse((HERE / 'candidate/normal_stop_current_owner.py').exists())
        self.assertFalse((HERE / 'candidate/validate_fresh_final_history_readonly.py').exists())

    def test_default_plan_is_inert_additions_only(self):
        example = (HERE / 'candidate/contract.example.json').read_bytes()
        self.assertFalse(json.loads(example)['fresh_handoff_approved'])
        files = install.payload(example)
        self.assertTrue(all(p.startswith(('/usr/local/lib/aura-boot-recovery/', '/etc/systemd/system/')) for p in files))
        self.assertNotIn('/etc/dfx-mgrd/default_firmware', files)
        self.assertNotIn('/usr/bin/dfx-mgr-client', files)
        self.assertNotIn(str(runtime.CHECKPOINT), files)

    def test_effective_candidate_dependency_graph_is_acyclic_and_ordered(self):
        audit = json.loads((HERE / 'evidence/SOURCE_AUDIT.json').read_bytes())
        names = {'kv260-repaired-zocl.service', 'dfx-mgr.service', 'aura-original-wide-prepare.service', CAMERA := rules.CAMERA, GUI := rules.GUI, 'aura-boot-ready.service'}
        graph = {name: set() for name in names}
        for name, props in audit['effective_historical_dependencies'].items():
            if name in graph:
                graph[name].update(set((props.get('After') or '').split()) & names)
        for path in (HERE / 'candidate/systemd').rglob('*'):
            if not path.is_file():
                continue
            name = path.parent.name[:-2] if path.parent.name.endswith('.d') else path.name
            for line in path.read_text().splitlines():
                if line.startswith('After='):
                    graph[name].update(set(line.split('=', 1)[1].split()) & names)
        ordered = list(graphlib.TopologicalSorter(graph).static_order())
        expected = ['kv260-repaired-zocl.service', 'dfx-mgr.service', 'aura-original-wide-prepare.service', CAMERA, GUI, 'aura-boot-ready.service']
        self.assertEqual(ordered, expected)

    def test_original_camera_entry_and_infinite_no_kill_boundary_are_retained(self):
        camera = (HERE / 'candidate/systemd/aura-camera-ui.service.d/90-aura-boot-recovery.conf').read_text()
        self.assertNotIn('\nExecStart=', camera)
        self.assertNotIn('TimeoutStopSec=', camera)
        self.assertNotIn('KillMode=', camera)
        self.assertIn('camera-check', camera)

    def test_no_new_motion_or_forced_lifecycle_entry(self):
        for name in install.PYTHON_FILES:
            raw = (HERE / 'candidate' / name).read_text()
            tree = ast.parse(raw)
            for node in ast.walk(tree):
                if isinstance(node, ast.List) and node.elts and isinstance(node.elts[0], ast.Constant) and node.elts[0].value == 'systemctl':
                    argv = [n.value for n in node.elts if isinstance(n, ast.Constant)]
                    self.assertFalse(set(argv) & {'start', 'stop', 'restart', 'kill', 'reboot', 'enable', 'disable'}, (name, argv))
            self.assertNotIn('import sqlite3', raw)
            self.assertNotIn('import ctypes', raw)
            self.assertNotIn('board_ssh', raw)
            self.assertNotIn('NativeContext(', raw)

    def test_runtime_refuses_windows_or_missing_activation_before_device_access(self):
        with patch.object(runtime.platform, 'system', return_value='Windows'):
            with self.assertRaisesRegex(rules.Hold, 'BOARD_ROOT'):
                runtime.Recovery('synthetic-not-a-board-path')


class SourceDriftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        self.base = Path(self.temp.name)
        self.state = self.base / 'state'
        self.state.mkdir()
        self.aura = self.base / 'runtime/aura'
        (self.aura / 'config').mkdir(parents=True)
        self.camera = self.base / 'camera.py'
        self.camera.write_bytes(b'original camera')
        self.selected = self.base / 'selected.json'
        selected_doc = dict(source_sha256={str(self.camera): rules.digest(self.camera.read_bytes())})
        self.selected.write_bytes(rules.encoded(selected_doc))
        spec = dict(path=str(self.selected), sha256=rules.digest(self.selected.read_bytes()))
        self.ui = self.aura / 'config/board_avatar_gtk.json'
        self.ui.write_bytes(rules.encoded(dict(board_business=dict(face_readback=spec))))
        (self.aura / 'identity.py').write_bytes(b'latest identity fix')
        (self.aura / 'gtk.py').write_bytes(b'latest GTK fix')
        pins = {name: rules.digest((self.aura / name).read_bytes()) for name in ('config/board_avatar_gtk.json', 'identity.py', 'gtk.py')}
        self.startup = self.base / 'startup.json'
        self.startup.write_bytes(rules.encoded(dict(runtime=str(self.aura.parent), component_sha256=pins)))
        self.r = object.__new__(runtime.Recovery)
        self.r.contract_sha = '7' * 64
        self.r.activation = {'installed_files': {}}
        self.r.contract = dict(startup_path=str(self.startup), runtime_aura=str(self.aura), component_count=3,
                               immutable_files={}, original_units={},
                               initial_source_state=dict(contract_sha256='INITIAL_CONTRACT',
                                                         startup_sha256=rules.digest(self.startup.read_bytes()),
                                                         ui_sha256=rules.digest(self.ui.read_bytes()), selected_pin=spec,
                                                         selected_sources=selected_doc['source_sha256']))
        self.patches = [patch.object(runtime, 'STATE_ROOT', self.state),
                        patch.object(runtime, 'regular', lambda p, limit=67108864: Path(p).read_bytes())]
        for value in self.patches:
            value.start()

    def tearDown(self):
        for value in reversed(self.patches):
            value.stop()
        checked_cleanup(self.temp)

    def test_exact_latest_sources_pass(self):
        self.r.source_snapshot()

    def test_new_identity_release_requires_fresh_sealing(self):
        value = json.loads(self.startup.read_bytes())
        (self.aura / 'identity.py').write_bytes(b'new peer identity release')
        value['component_sha256']['identity.py'] = rules.digest((self.aura / 'identity.py').read_bytes())
        self.startup.write_bytes(rules.encoded(value))
        with self.assertRaisesRegex(rules.Hold, 'RESEAL_REQUIRED'):
            self.r.source_snapshot()

    def test_file_only_change_is_not_accepted_by_old_pin(self):
        (self.aura / 'gtk.py').write_bytes(b'changed without pin')
        with self.assertRaisesRegex(rules.Hold, 'COMPONENT_SOURCE_CHANGED'):
            self.r.source_snapshot()

    def test_selected_camera_source_change_is_not_accepted(self):
        self.camera.write_bytes(b'changed camera candidate')
        with self.assertRaisesRegex(rules.Hold, 'CAMERA_SELECTED_SOURCE_CHANGED'):
            self.r.source_snapshot()

    def test_ledger_from_another_contract_is_rejected(self):
        active = dict(self.r.contract['initial_source_state'], contract_sha256='8' * 64)
        (self.state / 'active-source.json').write_bytes(rules.encoded(active))
        with self.assertRaisesRegex(rules.Hold, 'STATE_CONTRACT_CHANGED'):
            self.r.source_snapshot()

    def test_active_ledger_cannot_use_initial_sentinel_to_bypass_contract_binding(self):
        (self.state / 'active-source.json').write_bytes(rules.encoded(self.r.contract['initial_source_state']))
        with self.assertRaisesRegex(rules.Hold, 'STATE_CONTRACT_CHANGED'):
            self.r.source_snapshot()


class OrderedStartupQuietTests(unittest.TestCase):
    def test_queued_start_jobs_are_allowed_without_a_live_owner(self):
        r = object.__new__(runtime.Recovery)
        props = dict(MainPID='0', ControlPID='0', ActiveState='inactive', SubState='dead', Job='77')
        class EmptyProc:
            def iterdir(self):
                return []
        reply = subprocess.CompletedProcess([], 0, ('77 ' + rules.CAMERA + ' start waiting\n77 ' + rules.GUI + ' start waiting\n').encode(), b'')
        with patch.object(runtime, 'unit', return_value=props), patch.object(runtime, 'command', return_value=reply), patch.object(runtime, 'Path', return_value=EmptyProc()), patch.object(runtime, 'owner_scan', return_value=safe_scan()):
            r.quiet()

    def test_pending_stop_is_not_confused_with_an_ordered_start(self):
        r = object.__new__(runtime.Recovery)
        props = dict(MainPID='0', ControlPID='0', ActiveState='inactive', SubState='dead', Job='77')
        reply = subprocess.CompletedProcess([], 0, ('77 ' + rules.CAMERA + ' stop waiting\n77 ' + rules.GUI + ' start waiting\n').encode(), b'')
        with patch.object(runtime, 'unit', return_value=props), patch.object(runtime, 'command', return_value=reply):
            with self.assertRaisesRegex(rules.Hold, 'NOT_OUR_ORDERED_START'):
                r.quiet()

    def test_current_camera_mainpid_is_not_treated_as_a_queued_start(self):
        r = object.__new__(runtime.Recovery)
        props = dict(MainPID='1332', ControlPID='0', ActiveState='active', SubState='running', Job='')
        with patch.object(runtime, 'unit', return_value=props):
            with self.assertRaisesRegex(rules.Hold, 'EXISTING_SERVICE_OWNER'):
                r.quiet()


class BindingRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        self.base = Path(self.temp.name)
        self.state = self.base / 'state'
        self.package = self.base / 'package'
        self.package.mkdir()
        self.directory = self.state / 'boots' / BOOT / 'binding-701-12345'
        self.directory.mkdir(parents=True)
        self.aura = self.base / 'aura'
        (self.aura / 'config').mkdir(parents=True)
        self.ui = self.aura / 'config/board_avatar_gtk.json'
        self.startup = self.base / 'startup.json'
        self.ui_before, self.ui_after = b'original UI bytes', b'own UI after bytes'
        self.startup_before, self.startup_after = b'original startup bytes', b'own startup after bytes'
        self.ui.write_bytes(self.ui_after)
        self.startup.write_bytes(self.startup_after)
        contract_raw = rules.encoded(dict(startup_path=str(self.startup), runtime_aura=str(self.aura)))
        (self.package / 'contract.json').write_bytes(contract_raw)
        intent = dict(boot_id=BOOT, contract_sha256=rules.digest(contract_raw),
                      ui_before_sha256=rules.digest(self.ui_before), ui_after_sha256=rules.digest(self.ui_after),
                      startup_before_sha256=rules.digest(self.startup_before), startup_after_sha256=rules.digest(self.startup_after),
                      active_before_sha256=rules.digest(b'null\n'))
        for name, raw in [('intent.json', rules.encoded(intent)), ('ui.before.json', self.ui_before), ('ui.after.json', self.ui_after),
                          ('startup.before.json', self.startup_before), ('startup.after.json', self.startup_after),
                          ('active-source.before.json', b'null\n'), ('committed.json', b'{"own":"ledger"}\n')]:
            (self.directory / name).write_bytes(raw)
        (self.state / 'active-source.json').write_bytes(b'{"own":"ledger"}\n')
        real_path = Path
        class BootFile:
            def read_text(self):
                return BOOT
        def test_path(value):
            return BootFile() if str(value) == '/proc/sys/kernel/random/boot_id' else real_path(value)
        def cas(path, before, after):
            rules.require(real_path(path).read_bytes() == before, 'TEST_CAS_CONFLICT')
            real_path(path).write_bytes(after)
        stopped = dict(MainPID='0', ControlPID='0', ActiveState='inactive', SubState='dead', Job='', Result='success')
        self.patches = [patch.object(install, 'STATE_ROOT', self.state), patch.object(install, 'PACKAGE_ROOT', self.package),
                        patch.object(install, 'Path', test_path), patch.object(install, 'board_only'), patch.object(install, 'lock_state'),
                        patch.object(install, 'no_live_helpers_or_loader_jobs'), patch.object(install, 'unit', return_value=stopped),
                        patch.object(install, 'owner_scan', return_value=safe_scan()), patch.object(install, 'fsync_directory'),
                        patch.object(install, 'regular', lambda p, limit=67108864: real_path(p).read_bytes()),
                        patch.object(install, 'replace_known', cas)]
        for value in self.patches:
            value.start()

    def tearDown(self):
        for value in reversed(self.patches):
            value.stop()
        checked_cleanup(self.temp)

    def test_exact_known_byte_rollback_restores_both_and_leaves_services_stopped(self):
        result = install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_before)
        self.assertEqual(self.startup.read_bytes(), self.startup_before)
        self.assertFalse((self.state / 'active-source.json').exists())
        self.assertFalse(result['service_action_requested'])

    def test_newer_identity_startup_conflict_aborts_before_any_rollback(self):
        self.startup.write_bytes(b'newer peer identity deployment')
        with self.assertRaisesRegex(rules.Hold, 'NEWER_SOURCE_CONFLICT'):
            install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_after)

    def test_tampered_original_backup_is_not_a_rollback_source(self):
        (self.directory / 'ui.before.json').write_bytes(b'unknown bytes')
        with self.assertRaisesRegex(rules.Hold, 'SEALED_BYTES_CHANGED'):
            install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_after)

    def test_newer_binding_ledger_blocks_rollback(self):
        (self.state / 'active-source.json').write_bytes(b'newer ledger')
        with self.assertRaisesRegex(rules.Hold, 'NEWER_ACTIVE_LEDGER'):
            install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_after)

    def test_live_hardware_owner_blocks_rollback(self):
        with patch.object(install, 'owner_scan', return_value=dict(complete=True, owners=[OWNER], unreadable=[])):
            with self.assertRaisesRegex(rules.Hold, 'HARDWARE_OWNER'):
                install.rollback_binding(self.directory)
        self.assertEqual(self.ui.read_bytes(), self.ui_after)


if __name__ == '__main__':
    (HERE / 'test_work').mkdir(exist_ok=True)
    unittest.main(verbosity=2)
