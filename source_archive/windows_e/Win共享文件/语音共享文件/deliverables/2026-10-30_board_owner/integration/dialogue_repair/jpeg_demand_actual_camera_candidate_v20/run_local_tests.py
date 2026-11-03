"""Resolve every runtime import through the actual v20 audited source pins."""
import argparse
import hashlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import time
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
AUDIT = REPAIR / 'jpeg_demand_review_v20/SOURCE_AUDIT.json'
MAPPING = REPAIR / 'release_v20_identity_history_candidate/identity_history_evidence/source_mapping.json'
CAMERA = 'board/vision/ui_camera_service.py'
ACTUAL = REPAIR / 'jpeg_demand_review_v20/actual_camera_source_9d714'
CAMERA_BEFORE = '9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
PUBLIC_CONFIG_SHA = 'b6221c31638ab289eea81884440a50845f0f3028f05ee39e7d39a3a64f254d97'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_imports():
    assert sha(AUDIT) == '04fb3f09af3f2beeb365a1ded6b39f07292ef3aa098047ca78f73cf1a4f2ca6a'
    assert sha(MAPPING) == 'a7141992428e47d49ef80828ce9a0b33df6bffe32b613343ba01f937f68fdafc'
    audit = json.loads(AUDIT.read_text('utf-8'))
    pins = json.loads(MAPPING.read_text('utf-8'))['component_pins']
    sources = {}
    for row in audit['files']:
        component = row['component']
        source = Path(row['path'])
        assert sha(source) == row['sha256'] == pins[component], component
        package = component.endswith('/__init__.py')
        module = component[:-12] if package else component[:-3]
        sources[module.replace('/', '.')] = (source, package)
    assert len(sources) == 342
    assert sha(HERE / 'before' / CAMERA) == CAMERA_BEFORE
    readbacks = ('READBACK.json', 'ADDITIONAL_READBACK.json', 'DEPENDENCY_READBACK.json')
    for filename in readbacks:
        for row in json.loads((ACTUAL / filename).read_text('utf-8'))['files']:
            assert sha(Path(row['local_path'])) == row['sha256'], row['path']
    sources['board.vision.native_errors'] = (ACTUAL / '13_native_errors.py', False)
    sources['board.vision.pipeline_metrics'] = (ACTUAL / '14_pipeline_metrics.py', False)
    historical = REPAIR.parents[2] / '2026-10-24_native_critical_live'
    calibration = historical / 'source/aura/board/identity/calibration_http.py'
    release = json.loads((historical / 'release.json').read_text('utf-8'))
    assert release['deployment_path'] == '/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix'
    assert (sha(calibration) == release['files_sha256']['board/identity/calibration_http.py']
            == '42159f8b5a37c8bd0a86628df035d959cfd8ce8558b3433bf6b7b9fd01cfb621')
    sources['board.identity.calibration_http'] = (calibration, False)
    sources['board.vision.ui_camera_service'] = (HERE / 'after' / CAMERA, False)
    roots = {name.split('.')[0] for name in sources}

    class PinnedFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname in sources:
                source, package = sources[fullname]
                return importlib.util.spec_from_file_location(
                    fullname, source, submodule_search_locations=[str(source.parent)] if package else None)
            if fullname.split('.')[0] in roots:
                raise ModuleNotFoundError('Runtime import has no actual source pin: ' + fullname)
            return None

    sys.meta_path.insert(0, PinnedFinder())
    if sys.platform == 'win32':
        fcntl = types.ModuleType('fcntl')

        def forbidden(*args, **kwargs):
            raise AssertionError('POSIX locking is not emulated in these Windows tests')

        fcntl.flock = forbidden
        fcntl.LOCK_EX, fcntl.LOCK_NB, fcntl.LOCK_UN = 2, 4, 8
        sys.modules['fcntl'] = fcntl
    # Existing local dependencies only, no installation or download.
    dependencies = Path(r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
    if dependencies.exists():
        sys.path.append(str(dependencies))
    return pins


class UnavailablePlatformTest(unittest.TestCase):
    def __init__(self, test_id):
        super().__init__('runTest')
        self.test_id = test_id

    def id(self):
        return self.test_id

    def runTest(self):
        self.skipTest('Requires Linux file ownership, O_NOFOLLOW or POSIX mode 0600')


def platform_suite(suite):
    result = unittest.TestSuite()
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            result.addTests(platform_suite(test))
            continue
        name = test.id()
        raw_file_test = (name.startswith('tests.framework.test_local_camera_preview.')
                        and not name.endswith('test_local_transport_requires_opt_in_actual_source_and_loopback'))
        mode_test = name.endswith('StoreTests.test_connections_persist_without_changing_audio_preferences')
        result.addTest(UnavailablePlatformTest(name) if sys.platform == 'win32' and (raw_file_test or mode_test) else test)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='LOCAL_TEST_RESULT_01.json')
    args = parser.parse_args()
    pins = prepare_imports()
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    spec = importlib.util.spec_from_file_location('test_jpeg_demand', HERE / 'test_jpeg_demand.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    suite.addTests(loader.loadTestsFromModule(module))
    originals = ('test_camera_ui_service', 'test_yolo_dpu', 'test_board_ui_services',
                 'test_camera_identity', 'test_identity_face_targets', 'test_identity_capture_snapshot',
                 'test_media', 'test_local_camera_preview')
    for name in originals:
        suite.addTests(loader.loadTestsFromName('tests.framework.' + name))
    suite = platform_suite(suite)
    import common.config as configuration
    import host.model_service.schema as schema
    assert sha(HERE / 'fixtures/config/runtime.sim.json') == PUBLIC_CONFIG_SHA
    for row in json.loads((HERE / 'PUBLIC_FIXTURES.json').read_text('utf-8')):
        assert sha(HERE / 'fixtures' / row['component']) == row['sha256']
    log = io.StringIO()
    threads_before = {thread.ident for thread in threading.enumerate()}
    started = time.monotonic()
    with patch.object(configuration, 'PROJECT_ROOT', HERE / 'fixtures'):
        with patch.object(schema, 'PROJECT_ROOT', HERE / 'fixtures'):
            with patch.dict('os.environ', {'AURA_PIPELINE_METRICS': '0', 'AURA_DPU_DIAGNOSTICS': '0'}):
                result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    new_threads = [thread.name for thread in threading.enumerate() if thread.ident not in threads_before]
    output = HERE / args.output
    output.with_suffix('.log').write_text(log.getvalue(), encoding='utf-8')
    report = {
        'status': 'PASS' if result.wasSuccessful() and not new_threads else 'FAIL',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'seconds': round(time.monotonic() - started, 3),
        'audited_code_pins': 342, 'source_mapping_sha256': sha(MAPPING),
        'gui_copy_sha256': pins[CAMERA],
        'camera_before_sha256': CAMERA_BEFORE, 'camera_after_sha256': sha(HERE / 'after' / CAMERA),
        'test_sha256': sha(HERE / 'test_jpeg_demand.py'), 'runner_sha256': sha(Path(__file__)),
        'actual_camera_source_chain_readback': str(ACTUAL / 'READBACK.json'),
        'actual_camera_source_chain_readback_sha256': sha(ACTUAL / 'READBACK.json'),
        'actual_camera_source_chain_statically_reviewed': True,
        'actual_camera_after_deployed': False,
        'public_simulation_config_sha256': PUBLIC_CONFIG_SHA,
        'skipped_tests': [{'id': test.id(), 'reason': reason} for test, reason in result.skipped],
        'new_threads_remaining': new_threads,
        'platform': sys.platform,
        'limitations': [
            'Source chain is from root readback of camera 1335; candidate remains local only.',
            'OpenCV encoder is mocked; NumPy reshape and immutable BGR input are real.',
            'No physical camera, GTK, DPU, microphone, audio, model or real service was used.',
            'Original face HTTP test opens a synthetic localhost server on an ephemeral port.',
            'Five raw file tests and one 0600 mode test are explicit Windows platform skips.',
            'Native display uses public in-memory Gst/output fixtures, not physical screen acceptance.',
            'Original media tests use the hash-fixed public simulation config, absent from production pins.',
            'Original media tests use hash-fixed checked-in public JSON schemas, absent from production pins.',
            'native_errors/pipeline_metrics/local_preview are read from actual dependency paths, not claimed to be in the original 21 pins.',
            'calibration_http uses its historical exact native-r4 release pin; fresh device hash recheck is pending.',
        ],
        'failed_tests': [{'id': test.id(), 'traceback': error} for test, error in result.failures + result.errors],
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'failures', 'errors', 'seconds')}, ensure_ascii=False))
    if not result.wasSuccessful():
        print(log.getvalue()[-16000:])
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
