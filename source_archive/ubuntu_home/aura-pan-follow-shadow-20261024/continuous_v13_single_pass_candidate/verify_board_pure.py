"""Run real ARM Ruckig with fake PWM; no transport, camera or MMIO import."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'continuous-v13r1'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
assert platform.machine()=='aarch64'
manifest=json.loads((ROOT/'deployment-manifest.json').read_text())
assert all(hashlib.sha256(Path(row['destination']).read_bytes()).hexdigest()==row['sha256']
           for row in manifest['files'])
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer),contextlib.redirect_stderr(buffer):
    import test_recenter
    test_recenter.HERE=ROOT
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_continuity','test_recenter','test_renewal_reserve','test_single_pass'])
    result=unittest.TextTestRunner(stream=buffer,verbosity=1).run(suite)
print(json.dumps(dict(status='ARM_PURE_CONTROL_PASS' if result.wasSuccessful() else 'ARM_PURE_CONTROL_FAILED',
    tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
    consumer_manifest_sha256=hashlib.sha256((ROOT/'deployment-manifest.json').read_bytes()).hexdigest(),
    machine=platform.machine(),actuator='fake PWM device; native ARM Ruckig solver',
    motor_commands_sent=0,mmio_opened=False,camera_opened=False,
    error_details=buffer.getvalue()[-3000:] if not result.wasSuccessful() else '')))
if not result.wasSuccessful():raise SystemExit(1)
