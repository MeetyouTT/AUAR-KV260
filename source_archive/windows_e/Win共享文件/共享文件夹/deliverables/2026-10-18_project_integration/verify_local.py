"""Verify imported files/backups and run the Windows-compatible framework tests."""
import ast
import json
from pathlib import Path
import sys
import unittest
from integrate_from_e import HERE, TARGET, digest

LINUX_ONLY = {'test_audio_capture', 'test_camera_device', 'test_camera_ui_service',
              'test_local_camera_preview', 'test_yolo_dpu'}
POSIX_PERMISSIONS = {
    'test_board_ui_services.StoreTests.test_connections_persist_without_changing_audio_preferences',
    'test_transcription.BoundaryTests.test_configuration_is_persisted_and_invalid_changes_leave_previous',
}

def cases(suite):
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            yield from cases(entry)
        else:
            yield entry

def main():
    integration = json.loads((HERE / 'integration_result.json').read_text(encoding='utf-8'))
    for row in integration['files']:
        path = TARGET / row['path']
        assert digest(path) == row['source_sha256'], row['path']
        if row['action'] == 'replace':
            assert digest(HERE / 'before' / row['path']) == row['local_sha256'], row['path']
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=row['path'])
    aura = TARGET / 'aura'
    sys.path[:0] = [str(aura), str(aura / 'tests/framework')]
    modules = sorted(p.stem for p in (aura / 'tests/framework').glob('test_*.py') if p.stem not in LINUX_ONLY)
    loaded = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
    suite = unittest.TestSuite(case for case in cases(loaded) if case.id() not in POSIX_PERMISSIONS)
    with (HERE / 'framework_tests_windows.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {'status': 'PASS' if result.wasSuccessful() else 'FAILED',
              'integrated_file_hashes_checked': len(integration['files']),
              'verified_backups': integration['replaced'], 'windows_framework_tests': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'linux_only_modules_not_run': sorted(LINUX_ONLY),
              'posix_permission_tests_not_run': sorted(POSIX_PERMISSIONS),
              'permission_test_reason': 'Tests require POSIX file mode 0600; Windows st_mode reports 0666',
              'linux_only_reason': 'POSIX fcntl and O_NOFOLLOW/device semantics require Linux',
              'first_full_discovery': 'framework_tests_local.log retained: Windows lacks POSIX APIs; sandbox denied atomic replace and loopback',
              'hardware_or_live_models_tested': False,
              'python': sys.executable}
    (HERE / 'local_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    raise SystemExit(main())
