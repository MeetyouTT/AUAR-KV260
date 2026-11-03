import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(1,'/home/ghmd/aura-pan-joint-20261023/bundle/driver')
from pulse_driver import PulseDriver
from vsrv_driver import STOP,QUIESCE


class Registers:
    def __init__(self,mode):
        self.mode=mode;self.writes=[];self.quiescing=False
        self.values={0:0x56535256,4:2,8:0x778d2512,0x0c:15,0x28:3,0x2c:1482,
                     0x30:100,0x34:7,0x38:9,0x40:1478,0x44:1482}
    def read_many(self,offsets):
        if self.quiescing:
            if self.mode=='normal':self.values.update({0x0c:0,0x30:0})
            elif self.mode in ('expiry','mismatch'):
                self.values.update({0x0c:64,0x30:0})
                if self.mode=='mismatch':self.values[0x38]+=1
            elif self.mode=='fault':self.values[0x0c]=48
        return [self.values[n] for n in offsets]
    def read(self,n):return self.values[n]
    def write(self,n,v):
        self.writes.append((n,v))
        if n==0x24 and v==QUIESCE:self.quiescing=True
        if n==0x24 and v==STOP:self.quiescing=False;self.values.update({0x0c:0,0x30:0})


class PulseTests(unittest.TestCase):
    def device(self,mode):
        io=Registers(mode);d=PulseDriver(io,0x778d2512,'boot')
        d.session,d.epoch,d.ack_seq,d.accepted_target_us=7,9,3,1482
        return d,io
    def test_normal_completion_sends_only_quiesce(self):
        d,io=self.device('normal');self.assertEqual(d.finish()['flags'],0)
        self.assertEqual(io.writes,[(0x24,QUIESCE)])
    def test_exact_expiry_during_finish_confirms_stop_without_restarting(self):
        d,io=self.device('expiry');self.assertEqual(d.finish()['flags'],0)
        self.assertEqual(io.writes,[(0x24,QUIESCE),(0x24,STOP)])
    def test_other_hardware_fault_or_context_drift_remains_an_error(self):
        for mode in ['fault','mismatch']:
            with self.subTest(mode=mode):
                d,io=self.device(mode)
                with self.assertRaises(RuntimeError):d.finish()
                self.assertEqual(io.writes[-1],(0x24,STOP))


if __name__=='__main__':unittest.main()
