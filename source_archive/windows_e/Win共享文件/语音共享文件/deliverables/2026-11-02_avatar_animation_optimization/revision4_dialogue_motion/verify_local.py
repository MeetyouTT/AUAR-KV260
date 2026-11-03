from common import *
import unittest,importlib.util
p=HERE/'tests/test_adapter.py';spec=importlib.util.spec_from_file_location('r4_tests',p)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
save(HERE/'validation/ADAPTER_TESTS.json',dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
 errors=len(result.errors),failures=len(result.failures),candidate_adapter_sha256=sha(HERE/'candidate/runtime/tools/native_yuki.py'),
 baseline_adapter_sha256=sha(HERE/'baseline/runtime/tools/native_yuki.py'),device_calls=0))
assert result.wasSuccessful()
