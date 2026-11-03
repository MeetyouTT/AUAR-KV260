"""Record binding regression with exact source hashes; fake C ABI only."""
import hashlib
import io
import json
from pathlib import Path
import unittest

root = Path(__file__).resolve().parent
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromName('test_native_binding'))
report = {'passed': result.wasSuccessful(), 'tests': result.testsRun,
          'failures': len(result.failures), 'errors': len(result.errors),
          'log': stream.getvalue(), 'scope': 'Python binding fake C ABI; no DSO/model loaded',
          'source_sha256': {n: hashlib.sha256((root/n).read_bytes()).hexdigest()
                            for n in ('native_binding.py', 'test_native_binding.py')}}
(root/'binding-unit-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if k != 'log'}, indent=2))
raise SystemExit(0 if report['passed'] else 1)
