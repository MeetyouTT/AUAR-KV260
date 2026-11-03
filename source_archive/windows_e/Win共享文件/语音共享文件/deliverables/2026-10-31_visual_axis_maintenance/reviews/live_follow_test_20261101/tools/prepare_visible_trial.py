"""Prepare an attended 80us/6s diagnostic from the archived finite roundtrip bench."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]
BUSINESS=HERE.parents[3]
OLD=BUSINESS/'deliverables/2026-10-24_pan_board_trial/source/bench_observed_20us.py'
SCRIPTS=BUSINESS/'deliverables/2026-10-23_pan_joint_firmware/scripts'
sys.path.insert(0,str(SCRIPTS))
from test_finite_step import FakeClock,FakeHardware

def main():
    original=OLD.read_bytes();text=original.decode()
    text=text.replace('20us','80us').replace('20US_RETURN_2S','80US_RETURN_6S').replace('in two seconds','in six seconds')
    text=text.replace('origin+20','origin+80').replace("'excursion_us':20","'excursion_us':80")
    text=text.replace("'user_requested_excursion_us':20","'user_requested_excursion_us':80")
    text=text.replace("'excursion_us':20,","'excursion_us':80,")
    text=text.replace('((.5,origin),(1.5,origin+80),(2.,origin))','((1.,origin),(4.,origin+80),(6.,origin))')
    text=text.replace("'duration_s':2,'stages_seconds':[.5,1,.5]","'duration_s':6,'stages_seconds':[1,3,2]")
    text=text.replace('0x778d2512','0x10282601')
    before='                submitted=clock();state=device.status()'
    after='''                submitted=clock()
                if end-submitted<=.025:
                    sleep(max(0.,end-submitted))
                    break
                state=device.status()'''
    assert text.count(before)==1;text=text.replace(before,after)
    ast.parse(text)
    candidate=HERE/'package/bench_observed_80us_6s.py'
    candidate.write_text(text,encoding='utf-8',newline='\n')
    ns={'__name__':'visible_trial','__file__':str(candidate)};exec(compile(text,str(candidate),'exec'),ns)
    run=ns['run_roundtrip']
    class Checks(unittest.TestCase):
        def setUp(self):
            self.c=FakeClock();self.io=FakeHardware(self.c);self.events=[]
            self.io.width=self.io.target=self.io.reference=1505
            self.expected=self.io.status()
        def bench(self,sleep=None,expected=None,origin=1505):
            return run(self.io,self.io,origin,expected or self.expected,self.events,clock=self.c,sleep=sleep or self.c.sleep)
        def test_bounded_trip_returns_and_stops(self):
            result=self.bench();self.assertAlmostEqual(self.c.now,106.)
            self.assertEqual(result['stopped']['width_us'],1505);self.assertEqual(self.io.flags,0)
            self.assertEqual({e['target_us'] for e in self.events},{1505,1585})
            self.assertEqual(self.io.finishes,1)
        def test_out_of_range_rejected_before_setup(self):
            with self.assertRaises(RuntimeError):self.bench(origin=1525)
            self.assertEqual(self.io.commits,0);self.assertEqual(self.io.shadow,{})
        def test_changed_context_rejected(self):
            self.io.epoch=9
            with self.assertRaises(RuntimeError):self.bench()
            self.assertEqual(self.io.shadow,{})
        def test_late_shadow_cannot_commit(self):
            self.io.delay_shadow=True
            with self.assertRaisesRegex(RuntimeError,'Late COMMIT'):self.bench()
            self.assertEqual(self.io.commits,0);self.assertEqual(self.io.flags,0)
        def test_expiry_stops_without_retry(self):
            with self.assertRaisesRegex(RuntimeError,'Lease/context lost'):self.bench(sleep=lambda _:self.c.sleep(.11))
            self.assertEqual(self.io.commits,1);self.assertEqual(self.io.flags,0)
        def test_slow_status_keeps_deadline_and_returns(self):
            original=self.io.status
            def status():self.c.sleep(.006);return original()
            self.io.status=status
            result=self.bench();self.assertEqual(result['stopped']['width_us'],1505)
            self.assertLess(self.c.now-100.,6.15)
    with (HERE/'evidence/visible_trial_tests.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    raw=candidate.read_bytes()
    record=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        original_sha256=hashlib.sha256(original).hexdigest(),candidate_sha256=hashlib.sha256(raw).hexdigest(),
        attended_scope='1505 -> 1585 -> 1505 us, 6s maximum nominal stages, no automatic repeat',
        hardware_lease_ms=100,submission_limit_ms=25,device_accessed=False)
    (HERE/'evidence/visible_trial_tests.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    assert result.wasSuccessful()
    payload=dict(data=base64.b64encode(raw).decode(),sha256=record['candidate_sha256'])
    remote='''# USE_SESSION_COMMON
import base64
P=__PAYLOAD__
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='INITIALIZED_AWAITING_HUMAN_OBSERVATION'
assert j['current_stopped_readback']['width_us']==1505
raw=base64.b64decode(P['data'],validate=True);assert hashlib.sha256(raw).hexdigest()==P['sha256']
script=ROOT/'bench_observed_80us_6s.py'
with script.open('xb') as handle:handle.write(raw)
expected=ROOT/'visible-expected-state.json';atomic(expected,dict(boot_id=BOOT,registers=j['current_stopped_readback']))
atomic(ROOT/'visible-authorization.json',dict(boot=BOOT,source='user requested actual following and reported no visible motion',
 user_mount_and_clearance_confirmed=True,sequence_us=[1505,1585,1505],duration_s=6,
 physical_response_previously_observed=False,no_automatic_repeat=True))
output=ROOT/'visible-80us-roundtrip.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(script),'--execute','--confirmation','OBSERVED_80US_RETURN_6S',
 '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
 '--context',str(ROOT/'wide-context.json'),'--expected-state',str(expected),'--output',str(output)]
j.update(phase='VISIBLE_ROUNDTRIP_INTENT',visible_script_sha256=P['sha256']);save(j)
time.sleep(5)
p=subprocess.run(args,capture_output=True,text=True,timeout=12)
receipt=document(output)
if p.returncode!=0 or receipt.get('status')!='80US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING':
 j.update(phase='VISIBLE_ROUNDTRIP_FAILED_NO_RETRY',visible_receipt_sha256=digest(output));save(j)
 print(json.dumps(dict(status=j['phase'],returncode=p.returncode,receipt=receipt)));raise SystemExit(0)
stopped=receipt['result']['stopped'];assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1505
j.update(phase='VISIBLE_ROUNDTRIP_AWAITING_HUMAN',visible_receipt_sha256=digest(output),current_stopped_readback=stopped);save(j)
print(json.dumps(dict(status=j['phase'],sequence_us=receipt['result']['commanded_sequence_us'],
 commands=len(receipt['events']),minimum_width_us=min(e['width_us'] for e in receipt['events']),
 maximum_width_us=max(e['width_us'] for e in receipt['events']),stopped_readback=stopped,
 physical_observation='PENDING_USER',automatic_following=False)))
'''.replace('__PAYLOAD__',repr(payload))
    (HERE/'remote/visible_roundtrip.py').write_text(remote,encoding='utf-8',newline='\n')
    print(json.dumps(record))

if __name__=='__main__':main()
