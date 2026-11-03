import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(1, '/home/ghmd/aura-pan-joint-20261023/bundle/driver')
from lease_aware_driver import LeaseAwareDriver
from vsrv_driver import STOP, COMMIT


class Registers:
    def __init__(self, **changes):
        self.writes = []
        self.values = {0: 0x56535256, 4: 2, 8: 0x778d2512,
                       0x0c: 64, 0x28: 3, 0x2c: 1505, 0x30: 0,
                       0x34: 7, 0x38: 9, 0x40: 1500, 0x44: 1505}
        for name, value in changes.items():
            self.values[dict(flags=0x0c, session=0x34, epoch=0x38,
                             ack_seq=0x28, target_us=0x44)[name]] = value

    def read(self, offset):
        return self.values[offset]

    def write(self, offset, value):
        self.writes.append((offset, value))
        if offset == 0x24 and value == STOP:
            self.values[0x0c] = self.values[0x30] = 0


class LeaseRaceTests(unittest.TestCase):
    def submit(self, **changes):
        io = Registers(**changes)
        device = LeaseAwareDriver(io, 0x778d2512, 'boot', clock=lambda: 1.)
        device.reference = object()
        device.reference_time = .5
        device.session, device.epoch, device.ack_seq = 7, 9, 3
        device.accepted_target_us = 1505
        result = device.submit(1506, .95)
        self.assertEqual(io.values[0x0c], 0)
        self.assertEqual(io.writes, [(0x24, STOP)])
        self.assertIsNone(device.session)
        return result

    def test_exact_expiry_is_stopped_and_classified_before_flags_are_cleared(self):
        result = self.submit()
        self.assertEqual(result['reason'], 'SOURCE_LEASE_EXPIRED')
        self.assertEqual(result['rejected_readback']['flags'], 64)

    def test_context_mismatch_is_never_recoverable(self):
        for changes in [dict(session=8), dict(epoch=10), dict(ack_seq=4),
                        dict(target_us=1504), dict(ack_seq=0)]:
            with self.subTest(changes=changes):
                self.assertEqual(self.submit(**changes)['reason'], 'PERMISSION_OR_CONTEXT')

    def test_other_faults_or_inconsistent_expiry_are_never_recoverable(self):
        for flags in [0, 16, 32, 48, 65, 66]:
            with self.subTest(flags=flags):
                self.assertEqual(self.submit(flags=flags)['reason'], 'PERMISSION_OR_CONTEXT')

    def test_sequence_exhaustion_cannot_be_reclassified_as_expiry(self):
        io=Registers(ack_seq=0xffffffff)
        device=LeaseAwareDriver(io,0x778d2512,'boot',clock=lambda:1.)
        device.reference=object();device.reference_time=.5
        device.session,device.epoch,device.ack_seq=7,9,0xffffffff
        device.accepted_target_us=1505
        result=device.submit(1506,.95)
        self.assertEqual(result['reason'],'PERMISSION_OR_CONTEXT')
        self.assertEqual(io.writes,[(0x24,STOP)])


class CommitExpiryRegisters(Registers):
    def __init__(self):
        super().__init__(flags=15)
        self.values[0x30]=100;self.now=1.;self.commits=0
        self.fault_flags=32;self.fault_at=1.19;self.corrupt_shadow=False

    def write(self,offset,value):
        super().write(offset,value)
        if offset in (0x10,0x14,0x18,0x1c,0x20):self.values[offset]=value
        if offset==0x24 and value==COMMIT:
            self.commits+=1
            if self.commits==1:
                self.values[0x28]=self.values[0x18];self.values[0x44]=self.values[0x1c]
                self.values[0x30]=self.values[0x20]
            else:
                self.now=self.fault_at;self.values[0x0c]=self.fault_flags;self.values[0x30]=0
                if self.corrupt_shadow:self.values[0x1c]-=1


class CommitExpiryTests(unittest.TestCase):
    def run_race(self,*,flags=32,at=1.19,corrupt=False):
        io=CommitExpiryRegisters()
        device=LeaseAwareDriver(io,0x778d2512,'boot',clock=lambda:io.now)
        device.reference=object();device.reference_time=.5
        device.session,device.epoch,device.ack_seq=7,9,3
        device.accepted_target_us=1505
        self.assertEqual(device.submit(1506,.95)['outcome'],'ACCEPTED')
        io.now=1.17;io.fault_flags=flags;io.fault_at=at;io.corrupt_shadow=corrupt
        return device.submit(1507,1.15),io

    def test_expiry_between_preflight_and_commit_stops_and_requires_reconfirmation(self):
        result,io=self.run_race()
        self.assertEqual(result['reason'],'SOURCE_LEASE_EXPIRED')
        self.assertEqual(result['outcome'],'REJECTED')
        self.assertEqual(result['rejected_readback']['preflight']['flags'],15)
        self.assertEqual(io.writes[-1],(0x24,STOP))
        self.assertEqual(io.values[0x0c],0)

    def test_early_rejection_live_permission_or_corrupt_payload_stays_fatal(self):
        for options in [dict(at=1.171),dict(flags=47),dict(corrupt=True)]:
            with self.subTest(options=options):
                result,io=self.run_race(**options)
                self.assertEqual(result['reason'],'HARDWARE_REJECTED')
                self.assertEqual(result['outcome'],'REJECTED')
                self.assertNotEqual(io.writes[-1],(0x24,STOP))


if __name__ == '__main__':
    unittest.main()
