"""Run public regression cases and record fixed metadata without device access."""
import ast
import io
import json
import sys
import time
import unittest

import apply_rebind_closed
import rebind_common as common
import seal_rebind
import test_rebind


def main():
    started = time.monotonic()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_rebind)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    proposed = common.proposed(test_rebind.public_binding())
    applied = test_rebind.public_applied()
    sources = {'baseline': common.publisher_remote(common.baseline()),
               'applied': common.publisher_remote(applied),
               'apply': apply_rebind_closed.build_remote(proposed), 'seal': seal_rebind.build_remote(applied)}
    for source in sources.values():
        ast.parse(source, feature_version=(3, 9))
    report = {'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
              'elapsed_seconds': round(time.monotonic() - started, 3), 'public_synthetic_inputs_only': True,
              'ssh_called': False, 'production_database_opened': False, 'camera_or_model_opened': False,
              'real_posix_directory_permissions_tested': sys.platform != 'win32',
              'real_flock_tested': False, 'transaction_function_executed_unchanged': True,
              'apply_fault_injection_points': 11, 'intent_old_new_combinations': 8,
              'source_component_count': 380, 'component_changes': [common.CONFIG_RELATIVE],
              'other_component_bytes_changed': False, 'lifecycle_function_ast_changes': ['reviewed_face'],
              'dispatch_addition': 'APPLIED transaction and exact applied-spec proof before start/ready',
              'public_fixture_remote_sha256': {name: common.sha(source.encode()) for name, source in sources.items()},
              'test_output': stream.getvalue()}
    output = common.HERE / 'LOCAL_TEST_RESULT.json'
    if output.exists():
        output = common.HERE / ('LOCAL_TEST_RESULT_' + str(time.time_ns()) + '.json')
    output.write_bytes(common.encoded(report))
    report['output'] = str(output)
    print(json.dumps({key: value for key, value in report.items() if key != 'test_output'}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
