"""Offline v20 binding and refusal tests, with all device surfaces replaced."""
from contextlib import ExitStack
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import probe_small_threads as probe
from test_probe import ProbeTests


HERE = Path(__file__).resolve().parent


class MetadataPath:
    def __init__(self, value):
        self.value = str(value)

    def __truediv__(self, part):
        return MetadataPath(self.value.rstrip('/') + '/' + str(part))

    def read_text(self):
        if self.value == '/proc/sys/kernel/random/boot_id':
            return probe.BOOT
        raise AssertionError('Unmocked file read')


class V20Bindings(unittest.TestCase):
    def setUp(self):
        self.baseline = json.loads((HERE/'baseline.json').read_bytes())
        self.startup = dict(component_sha256=copy.deepcopy(self.baseline['component_pins']))
        self.config = dict(board_business=dict(asr_variant='paraformer_small', asr_threads=3,
                                               asr_directory=probe.MODEL_DIR))
        self.state = dict(phase='IDLE', playing=False,
            handsfree_dialogue=dict(enabled=False, microphone_open=False, state='PAUSED'),
            local_transcription=dict(state='IDLE'),
            avatar_display=dict(visible=True, frame_scheduling_active=True, frames=10,
                                paint_at=12., age_ms=15.),
            board_business=dict(memory=dict(completed=2, discarded=0)))
        self.camera = dict(pid=1335, capture_frames=10, detected_frames=9, preview_frames=9,
                           capture_age_ms=25, observation_age_ms=30, last_inference_ms=20)
        self.owners = {self.baseline[role]['pid']: copy.deepcopy(self.baseline[role])
                       for role in ('supervisor','gtk','camera')}

    def guarded(self, baseline=None):
        def read_pinned(path, expected, maximum=262144):
            if path.value.endswith('/startup/config.json'):
                self.assertEqual(expected, probe.STARTUP)
                return json.dumps(self.startup).encode()
            if path.value.endswith('/config/board_avatar_gtk.json'):
                self.assertEqual(expected, probe.CONFIG_SHA)
                return json.dumps(self.config).encode()
            raise AssertionError('Unmocked pinned file read')
        def metadata(port, route):
            if (port,route) == (8783,'/api/state'):
                return self.state
            if (port,route) == (8790,'/health'):
                return self.camera
            raise AssertionError('Unexpected endpoint')
        with ExitStack() as stack:
            stack.enter_context(patch.object(probe,'Path',MetadataPath))
            stack.enter_context(patch.object(probe,'read_pinned',read_pinned))
            stack.enter_context(patch.object(probe,'process_identity',lambda pid:self.owners[pid]))
            stack.enter_context(patch.object(probe,'get_metadata',metadata))
            stack.enter_context(patch.object(probe,'available_mib',lambda:2048.))
            return probe.guard(self.baseline if baseline is None else baseline)

    def test_v20_package_dry_validates_380_and_exact_owners(self):
        digest = probe.sha((HERE/'PACKAGE_MANIFEST.json').read_bytes())
        baseline = probe.package(digest)
        self.assertEqual(len(baseline['component_pins']),380)
        self.assertEqual([baseline[role]['pid'] for role in ('supervisor','gtk','camera')],
                         [121485,121489,1335])
        self.assertEqual(baseline['startup_sha256'],probe.STARTUP)
        with patch.object(sys,'argv',['probe','--package-sha256',digest]), \
                patch.object(probe,'guard',side_effect=AssertionError('device access in dry mode')):
            self.assertEqual(probe.main()['status'],'DRY_PACKAGE_VALIDATED')

    def test_paused_visible_matching_owners_are_required_and_accepted(self):
        result = self.guarded()
        self.assertTrue(result['listening_paused'])
        self.assertTrue(result['owners_verified'])

    def test_old_component_count_and_changed_map_are_refused(self):
        old = copy.deepcopy(self.baseline)
        old['component_pins'].pop('board/runtime/history_delete.py')
        with self.assertRaisesRegex(probe.Refused,'COMPONENT_MAP_CHANGED'):
            self.guarded(old)
        self.startup['component_sha256']['common/board_memory.py'] = '0'*64
        with self.assertRaisesRegex(probe.Refused,'COMPONENT_MAP_CHANGED'):
            self.guarded()

    def test_process_restart_refuses_even_with_same_pid(self):
        self.owners[121489]['birth_ticks'] += 1
        with self.assertRaisesRegex(probe.Refused,'PRODUCTION_OWNER_CHANGED'):
            self.guarded()

    def test_listening_playing_or_invisible_gui_refuses(self):
        for field in ('enabled','microphone_open'):
            with self.subTest(field=field):
                self.state['handsfree_dialogue'][field] = True
                with self.assertRaisesRegex(probe.Refused,'ROOT_MUST_PAUSE_REAL_CAPTURE_FIRST'):
                    self.guarded()
                self.state['handsfree_dialogue'][field] = False
        self.state['playing'] = True
        with self.assertRaisesRegex(probe.Refused,'ROOT_MUST_PAUSE_REAL_CAPTURE_FIRST'):
            self.guarded()
        self.state['playing'] = False
        self.state['avatar_display']['visible'] = False
        with self.assertRaisesRegex(probe.Refused,'GUI_MUST_REMAIN_VISIBLE'):
            self.guarded()

    def test_unreviewed_asr_config_or_camera_owner_refuses(self):
        self.config['board_business']['asr_threads'] = 2
        with self.assertRaisesRegex(probe.Refused,'PRODUCTION_ASR_CONFIGURATION_CHANGED'):
            self.guarded()
        self.config['board_business']['asr_threads'] = 3
        self.camera['pid'] = 1
        with self.assertRaisesRegex(probe.Refused,'CAMERA_HEALTH_OWNER_CHANGED'):
            self.guarded()


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ProbeTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(V20Bindings))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests=result.testsRun,
        errors=len(result.errors),failures=len(result.failures),log=stream.getvalue(),
        live_device_model_private_database_or_network_access=False,
        package_sha256=probe.sha((HERE/'PACKAGE_MANIFEST.json').read_bytes()))
    report_path = HERE/'LOCAL_TESTS_V20.json'
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if result.wasSuccessful():
        handoff_path = HERE/'HANDOFF.json'
        handoff = json.loads(handoff_path.read_bytes())
        handoff['status'] = 'LOCAL_READY_NO_DEVICE_OR_MODEL_EXECUTION'
        handoff['local_tests'] = dict(path=str(report_path),sha256=probe.sha(report_path.read_bytes()),passed=result.testsRun)
        handoff['test_source_sha256'] = probe.sha(Path(__file__).read_bytes())
        handoff_path.write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
