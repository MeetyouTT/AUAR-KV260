"""Keep the finite bench's deadline intact while skipping a final command that cannot fit."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]
BUSINESS=HERE.parents[3]
ORIGINAL_SCRIPTS=BUSINESS/'deliverables/2026-10-23_pan_joint_firmware/scripts'
sys.path[:0]=[str(ORIGINAL_SCRIPTS),str(HERE/'tests')]
from test_finite_step import FakeClock,FakeHardware,FiniteStepTests

def main():
    path=HERE/'package/bench_finite_step.py'
    original=path.read_bytes()
    assert hashlib.sha256(original).hexdigest()=='97bbd20fca86704cf34549b663f09e9ede0e0a3a3608625f659fe987e829c1ca'
    before="                submitted = clock()\n                state = device.status()"
    after="""                submitted = clock()
                # Do not start shadow writes when the phase cannot contain the
                # existing 25ms submission allowance. Keep the original phase
                # deadline and lease; wait out only the bounded remainder.
                if end - submitted <= .025:
                    sleep(max(0., end - submitted))
                    break
                state = device.status()"""
    source=original.decode();assert source.count(before)==1
    fixed=source.replace(before,after).encode();ast.parse(fixed)
    candidate=HERE/'package/bench_finite_step_deadline_fix.py';candidate.write_bytes(fixed)
    baseline_ns={'__name__':'baseline_finite','__file__':str(path)}
    fixed_ns={'__name__':'fixed_finite','__file__':str(candidate)}
    exec(compile(original,str(path),'exec'),baseline_ns)
    exec(compile(fixed,str(candidate),'exec'),fixed_ns)
    class SlowStatus(FakeHardware):
        def status(self):self.clock.sleep(.006);return super().status()
    class DeadlineWitness(unittest.TestCase):
        def test_old_code_reproduces_boundary_rejection(self):
            c=FakeClock();io=SlowStatus(c)
            with self.assertRaisesRegex(RuntimeError,'Late submission refused'):
                baseline_ns['run_finite'](io,io,1500,1505,[],clock=c,sleep=c.sleep)
            self.assertEqual(io.flags,0)
        def test_realistic_status_latency_completes_without_extending_deadline(self):
            c=FakeClock();io=SlowStatus(c);events=[]
            result=fixed_ns['run_finite'](io,io,1500,1505,events,clock=c,sleep=c.sleep)
            self.assertEqual(result['stopped']['width_us'],1505)
            self.assertEqual(result['stopped']['flags'],0)
            self.assertEqual(io.finishes,1)
            self.assertLess(c.now-100.,2.15)
            self.assertEqual({e['target_us'] for e in events},{1500,1505})
    # Rebind the original six tests to the changed function, leaving all old
    # late-shadow, lease-expiry and finite-bounds checks in place.
    import test_finite_step
    test_finite_step.run_finite=fixed_ns['run_finite']
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(FiniteStepTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(DeadlineWitness)])
    with (HERE/'evidence/finite_deadline_fix_tests.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    record=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        baseline_sha256=hashlib.sha256(original).hexdigest(),fixed_sha256=hashlib.sha256(fixed).hexdigest(),
        source_deadline_extended=False,lease_or_25ms_check_changed=False,device_opened=False)
    (HERE/'evidence/finite_deadline_fix_tests.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    assert result.wasSuccessful()
    (HERE/'package/finite_deadline_fix_payload.json').write_text(json.dumps(dict(
        data=base64.b64encode(fixed).decode(),sha256=record['fixed_sha256']))+'\n',encoding='utf-8')
    print(json.dumps(record))

if __name__=='__main__':main()
