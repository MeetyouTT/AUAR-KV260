import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_lease_aware_driver import Registers,CommitExpiryRegisters
from batch_driver import BatchDriver


class Batched(Registers):
    def __init__(self):super().__init__(flags=0);self.batches=0;self.race=False
    def read_many(self,offsets):
        self.batches+=1
        values=[self.read(n) for n in offsets]
        if self.race and len(offsets)>3:values[-1]+=1
        return values


class BatchTests(unittest.TestCase):
    def test_status_is_one_platform_transaction_with_identity_and_sequence_fences(self):
        io=Batched();device=BatchDriver(io,0x778d2512,'boot');io.batches=0
        state=device.status()
        self.assertEqual(io.batches,1);self.assertEqual(state['flags'],0)
        self.assertEqual(state['ack_seq'],3);self.assertEqual(io.writes,[])

    def test_identity_or_unstable_sequence_still_rejects_without_writes(self):
        for mode in ['identity','sequence']:
            io=Batched();device=BatchDriver(io,0x778d2512,'boot')
            if mode=='identity':io.values[8]+=1
            else:io.race=True
            with self.assertRaises(RuntimeError):device.status()
            self.assertEqual(io.writes,[])

    def test_submit_proxy_keeps_batch_reads_and_exact_expiry_classification(self):
        class R(CommitExpiryRegisters):
            def read_many(self,offsets):return [self.read(n) for n in offsets]
        io=R();device=BatchDriver(io,0x778d2512,'boot',clock=lambda:io.now)
        device.reference=object();device.reference_time=.5
        device.session,device.epoch,device.ack_seq=7,9,3;device.accepted_target_us=1505
        self.assertEqual(device.submit(1506,.95)['outcome'],'ACCEPTED')
        io.now=1.17
        self.assertEqual(device.submit(1507,1.15)['reason'],'SOURCE_LEASE_EXPIRED')


if __name__=='__main__':unittest.main()
