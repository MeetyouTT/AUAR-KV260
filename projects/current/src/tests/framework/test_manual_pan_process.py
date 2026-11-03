"""Real process/IPC regressions with a fake, expiring hardware lease."""
import multiprocessing
import os
import signal
import sys
import time
import unittest

from board.motion.manual_process import ManualPanProcess, backend
from test_manual_pan import Hardware, wait_for


class LeaseHardware(Hardware):
    def __init__(self):
        super().__init__(1450)
        self.last_commit = None

    def commit(self, target):
        now = time.monotonic()
        if self.last_commit is not None and now-self.last_commit > .1:
            raise RuntimeError('Simulated 100ms lease expired')
        self.last_commit = now
        return super().commit(target)


def fake_backend(connection, config):
    backend(connection, config, transport_factory=LeaseHardware)


def wait_process(predicate, seconds=5):
    end=time.monotonic()+seconds
    while not predicate():
        if time.monotonic()>end:raise AssertionError('Process timeout')
        time.sleep(.01)


class ManualProcessTests(unittest.TestCase):
    def start(self):
        pan=ManualPanProcess({},target=fake_backend)
        self.addCleanup(pan.close)
        wait_process(lambda:pan.read()['state']=='READY')
        return pan

    def test_startup_is_separate_process_and_sends_no_movement(self):
        pan=self.start()
        self.assertNotEqual(pan.read()['backend_pid'],os.getpid())
        self.assertEqual(pan.read()['history'],[])
        self.assertEqual(pan.read()['pulse_us'],1450)

    def test_parent_gil_stall_does_not_expire_child_lease(self):
        pan=self.start();pan.jog('right',5)
        wait_process(lambda:pan.read().get('readback',{}).get('flags')==15)
        old=sys.getswitchinterval()
        try:
            sys.setswitchinterval(.5)
            end=time.monotonic()+.35
            while time.monotonic()<end:pass
        finally:sys.setswitchinterval(old)
        wait_process(lambda:pan.read()['state']=='READY')
        self.assertEqual(pan.read()['pulse_us'],1455)
        self.assertGreaterEqual(pan.read()['history'][-1]['commands_accepted'],40)
        self.assertIsNone(pan.read()['history'][-1]['failure'])

    def test_stop_reaches_child_and_does_not_replay(self):
        pan=self.start();pan.jog('right',5)
        wait_process(lambda:pan.read().get('readback',{}).get('flags')==15)
        pan.stop();wait_process(lambda:pan.read()['state']=='READY')
        self.assertTrue(pan.read()['history'][-1]['stopped_early'])
        self.assertEqual(pan.read()['readback']['flags'],0)
        time.sleep(.2);self.assertEqual(len(pan.read()['history']),1)

    def test_expired_ipc_intent_cannot_start(self):
        context=multiprocessing.get_context('spawn');parent,child=context.Pipe()
        process=context.Process(target=fake_backend,args=(child,{}));process.start();child.close()
        try:
            while True:
                response=parent.recv()
                if response['kind']=='state' and response['value']['state']=='READY':break
            parent.send(dict(kind='jog',id='expired',issued=time.monotonic()-2,direction='right',step_us=5))
            while True:
                response=parent.recv()
                if response['kind']=='ack':break
            self.assertFalse(response['ok'])
            self.assertEqual(response['state']['history'],[])
            self.assertEqual(response['state']['pulse_us'],1450)
        finally:
            parent.send(dict(kind='close'));process.join(3);parent.close()
            if process.is_alive():process.kill();process.join()

    def test_child_exit_fault_and_explicit_reconnect_without_replay(self):
        pan=self.start();pid=pan.read()['backend_pid']
        os.kill(pid,signal.SIGKILL)
        wait_process(lambda:pan.read()['state'] in ('FAULT','UNAVAILABLE'))
        pan.reconnect();wait_process(lambda:pan.read()['state']=='READY')
        self.assertNotEqual(pan.read()['backend_pid'],pid)
        self.assertEqual(pan.read()['history'],[])

    def test_busy_cannot_reconnect_or_queue_extra_movement(self):
        pan=self.start();pan.jog('left',5)
        with self.assertRaises(ValueError):pan.jog('left',5)
        with self.assertRaises(ValueError):pan.reconnect()
        pan.stop();wait_process(lambda:pan.read()['state']=='READY')


if __name__=='__main__':unittest.main()
