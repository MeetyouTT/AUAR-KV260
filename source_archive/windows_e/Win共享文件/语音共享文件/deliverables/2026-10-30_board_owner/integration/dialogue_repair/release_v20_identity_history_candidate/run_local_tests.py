"""Local source/clock/socket fixtures. No production or network actions."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

import stability_common as common
import test_saved_pause
import test_stability_release
import test_added_component
import test_seal_stability


HERE = Path(__file__).resolve().parent
path = common.REPAIR / 'release_v18_minor_ui_candidate/port_release_wait_candidate/test_ownerless_port_wait.py'
expected = 'bac051365f6c77a79b646f74b98f9c3d057755a5415807f859e3d5f32b8a5762'
common.pinned(path, expected)
spec = importlib.util.spec_from_file_location('_original_port_wait_fixture_tests', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(item)
                           for item in (test_stability_release, test_saved_pause, test_added_component, test_seal_stability, module))
output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
pins = json.loads((HERE / 'BASE_INPUT_PINS.json').read_bytes())
for path, pin in pins.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == pin
value = {'status': 'PASS_LOCAL_ONLY' if result.wasSuccessful() else 'FAIL',
         'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
         'skipped': len(result.skipped), 'results': output.getvalue(),
         'prior_frozen_files_and_author_sources_unchanged': True,
         'devices_models_private_stores_or_production_sources_accessed': False,
         'real_linux_listener_test_pending': True}
(HERE / 'LOCAL_TEST_RESULT.json').write_bytes(common.encoded(value))
print(output.getvalue())
raise SystemExit(0 if result.wasSuccessful() else 1)
