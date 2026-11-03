import importlib.util
from pathlib import Path
import socket
import threading
import time
import unittest

source=Path('/home/ghmd/Win共享文件/共享文件夹/aura/scripts/board_ui_startup/launcher.py')
spec=importlib.util.spec_from_file_location('candidate_launcher',str(source))
launcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class PortTests(unittest.TestCase):
    def setUp(self):
        launcher.STOP.clear()
        self.addCleanup(launcher.STOP.clear)

    def listener(self):
        sock=socket.socket()
        sock.bind(('127.0.0.1',0));sock.listen(1)
        self.addCleanup(sock.close)
        return sock,sock.getsockname()[1]

    def test_waits_for_release_without_terminating_owner(self):
        sock,port=self.listener()
        thread=threading.Thread(target=lambda:(time.sleep(.35),sock.close()))
        thread.start()
        try:
            begin=time.monotonic()
            launcher.check_port_unused(port,wait_seconds=2)
            self.assertGreaterEqual(time.monotonic()-begin,.3)
        finally:thread.join()

    def test_occupied_port_has_bounded_failure(self):
        sock,port=self.listener()
        with self.assertRaises(OSError):launcher.check_port_unused(port,wait_seconds=.1)
        self.assertEqual(sock.getsockname()[1],port)

    def test_stop_interrupts_wait(self):
        sock,port=self.listener()
        launcher.STOP.set()
        with self.assertRaisesRegex(RuntimeError,'cancelled'):launcher.check_port_unused(port,wait_seconds=2)


if __name__=='__main__':unittest.main(verbosity=2)
