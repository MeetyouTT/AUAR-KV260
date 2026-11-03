from types import SimpleNamespace
import unittest
from manual_restore import restore_owned


class Ops:
    def __init__(self,original=False,fail=False):
        self.original=original;self.fail=fail;self.events=[];self.meta={};self.m=SimpleNamespace(command=self.command)
    def verify(self):self.events.append('verify')
    def ready(self,target):return self.original
    def assert_idle_or_stopped(self):self.events.append('idle')
    def save_meta(self):pass
    def command(self,args,timeout):self.events.append('arm')
    def restore(self):
        self.events.append('restore');assert self.meta['guard_armed']
        if self.fail:raise RuntimeError('injected')
        self.original=True;return {'restored':True}
    def disarm(self):self.events.append('disarm');assert self.original


class ManualTests(unittest.TestCase):
    def test_already_original_is_idempotent(self):
        ops=Ops(original=True);self.assertTrue(restore_owned(ops,'/owned/rollback.py')['passed'])
        self.assertNotIn('arm',ops.events)
    def test_restore_is_independently_armed_before_switching(self):
        ops=Ops();result=restore_owned(ops,'/owned/rollback.py')
        self.assertTrue(result['passed']);self.assertLess(ops.events.index('arm'),ops.events.index('restore'))
        self.assertEqual(ops.events[-1],'disarm')
    def test_failed_restore_keeps_guard_armed(self):
        ops=Ops(fail=True);result=restore_owned(ops,'/owned/rollback.py')
        self.assertFalse(result['passed']);self.assertTrue(result['guard_left_armed']);self.assertNotIn('disarm',ops.events)


if __name__=='__main__':unittest.main()
