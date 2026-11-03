"""Resolve every runtime import through the actual v20 audited source pins."""
import argparse
import hashlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import types
import unittest

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
AUDIT = REPAIR / 'jpeg_demand_review_v20/SOURCE_AUDIT.json'
MAPPING = REPAIR / 'release_v20_identity_history_candidate/identity_history_evidence/source_mapping.json'
CAMERA = 'board/vision/ui_camera_service.py'


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
    assert sha(HERE / 'before' / CAMERA) == pins[CAMERA]
    sources['board.vision.ui_camera_service'] = (HERE / 'after' / CAMERA, False)

    class PinnedFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname in sources:
                source, package = sources[fullname]
                return importlib.util.spec_from_file_location(
                    fullname, source, submodule_search_locations=[str(source.parent)] if package else None)
            if fullname.split('.')[0] in ('board', 'common', 'tools', 'tests'):
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
                 'test_media')
    for name in originals:
        suite.addTests(loader.loadTestsFromName('tests.framework.' + name))
    # This one original raw test has no POSIX file operations.
    suite.addTests(loader.loadTestsFromName(
        'tests.framework.test_local_camera_preview.LocalPreviewTests.'
        'test_local_transport_requires_opt_in_actual_source_and_loopback'))
    log = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    output = HERE / args.output
    output.with_suffix('.log').write_text(log.getvalue(), encoding='utf-8')
    report = {
        'status': 'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'seconds': round(time.monotonic() - started, 3),
        'audited_code_pins': 342, 'source_mapping_sha256': sha(MAPPING),
        'camera_before_sha256': pins[CAMERA], 'camera_after_sha256': sha(HERE / 'after' / CAMERA),
        'test_sha256': sha(HERE / 'test_jpeg_demand.py'), 'runner_sha256': sha(Path(__file__)),
        'actual_camera_loaded_source_verified': False,
        'platform': sys.platform,
        'limitations': [
            'Real camera executable/source chain still requires read-only verification by root.',
            'OpenCV encoder is mocked; NumPy reshape and immutable BGR input are real.',
            'No physical camera, GTK, DPU, microphone, audio, model or network request was used.',
            'Five original raw file tests require Linux ownership/O_NOFOLLOW and are not selected on Windows.',
            'Native display uses public in-memory Gst/output fixtures, not physical screen acceptance.',
        ],
        'failed_tests': [{'id': test.id(), 'traceback': error} for test, error in result.failures + result.errors],
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'failures', 'errors', 'seconds')}, ensure_ascii=False))
    if not result.wasSuccessful():
        print(log.getvalue()[-16000:])
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
