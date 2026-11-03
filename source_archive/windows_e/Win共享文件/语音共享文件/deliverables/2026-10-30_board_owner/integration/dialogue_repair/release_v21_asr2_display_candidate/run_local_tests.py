"""Run local configuration/source publication fixtures without device access."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

import stability_common as common
import test_configuration_closure
import test_saved_pause
import test_seal_stability


path = common.REPAIR / 'release_v18_minor_ui_candidate/port_release_wait_candidate/test_ownerless_port_wait.py'
common.pinned(path, 'bac051365f6c77a79b646f74b98f9c3d057755a5415807f859e3d5f32b8a5762')
spec = importlib.util.spec_from_file_location('_original_port_wait_tests_v21', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(item) for item in
    (test_configuration_closure, test_saved_pause, test_seal_stability, module))
output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
inputs = json.loads((common.HERE / 'BASE_INPUT_PINS.json').read_bytes())
for path, digest in inputs.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
value = dict(status='PASS_LOCAL_ONLY' if result.wasSuccessful() else 'FAIL',
    tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
    results=output.getvalue(), original_inputs_unchanged=True, device_access=False, models_executed=False,
    real_linux_listener_check_pending=True)
(common.HERE / 'LOCAL_TEST_RESULT.json').write_bytes(common.encoded(value))
print(output.getvalue())
raise SystemExit(0 if result.wasSuccessful() else 1)
