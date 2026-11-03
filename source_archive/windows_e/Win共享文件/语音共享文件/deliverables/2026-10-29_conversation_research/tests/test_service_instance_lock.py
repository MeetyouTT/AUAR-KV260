"""Mock both OS protocols; run native concurrency only on owned temp files."""
import errno
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'candidate' / 'tools'
sys.path.insert(0, str(TOOLS))
import service_instance_lock as module
from service_instance_lock import ServiceAlreadyRunning, ServiceInstanceLock

WORKER = r'''
import json,os,sys
sys.path.insert(0,sys.argv[1])
from service_instance_lock import ServiceAlreadyRunning,ServiceInstanceLock
if sys.argv[3]=='race':sys.stdin.readline()
try:
    lock=ServiceInstanceLock(sys.argv[2]).acquire()
except ServiceAlreadyRunning:
    print('BUSY',flush=True);raise SystemExit(0)
print('HELD',flush=True)
if sys.argv[3]=='exit':os._exit(0)
sys.stdin.readline()
lock.release()
print('RELEASED',flush=True)
'''


class LockTests(unittest.TestCase):
    def setUp(self):
        owned_root = Path(__file__).resolve().parent
        self.tmp = tempfile.TemporaryDirectory(prefix='aura-owned-lock-test-', dir=owned_root)
        if not Path(self.tmp.name).resolve().is_relative_to(owned_root):
            raise RuntimeError('Temporary lock fixture left its owned workspace')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'service.lock'
        self.children = []
        self.addCleanup(self.finish_children)

    def finish_children(self):
        for child in self.children:
            if child.poll() is None:
                try:
                    child.stdin.write('release\n'); child.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                # Only test children created above, never a project service.
                child.kill(); child.communicate(timeout=5)

    def worker(self, mode='hold'):
        child = subprocess.Popen([sys.executable, '-B', '-u', '-c', WORKER, str(TOOLS), str(self.path), mode],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.children.append(child)
        return child

    def test_windows_protocol_locks_byte_zero_without_wait(self):
        calls = []
        fake = types.SimpleNamespace(LK_NBLCK=19, LK_UNLCK=20, locking=lambda *args: calls.append(args))
        with patch.dict(sys.modules, {'msvcrt': fake}), patch.object(module.os, 'lseek') as seek:
            module._lock_fd(71, platform='nt'); module._unlock_fd(71, platform='nt')
        self.assertEqual(calls, [(71, 19, 1), (71, 20, 1)])
        self.assertEqual(seek.call_args_list[0].args, (71, 0, os.SEEK_SET))

    def test_posix_protocol_is_nonblocking_exclusive(self):
        calls = []
        fake = types.SimpleNamespace(LOCK_EX=4, LOCK_NB=8, LOCK_UN=16, flock=lambda *args: calls.append(args))
        with patch.dict(sys.modules, {'fcntl': fake}):
            module._lock_fd(72, platform='posix'); module._unlock_fd(72, platform='posix')
        self.assertEqual(calls, [(72, 12), (72, 16)])

    def test_empty_native_file_is_not_written_or_deleted(self):
        with ServiceInstanceLock(self.path) as held:
            self.assertTrue(held.held)
            self.assertFalse(os.get_inheritable(held._fd))
        self.assertTrue(self.path.is_file())
        self.assertEqual(self.path.read_bytes(), b'')

    def test_existing_contents_are_preserved(self):
        self.path.write_bytes(b'owned-existing-marker\n')
        with ServiceInstanceLock(self.path):
            pass
        self.assertEqual(self.path.read_bytes(), b'owned-existing-marker\n')

    def test_second_open_in_same_process_is_busy(self):
        with ServiceInstanceLock(self.path):
            with self.assertRaises(ServiceAlreadyRunning):
                ServiceInstanceLock(self.path).acquire()

    def test_exception_context_releases_and_release_is_idempotent(self):
        lock = ServiceInstanceLock(self.path)
        with self.assertRaisesRegex(ValueError, 'fixture'):
            with lock:
                raise ValueError('fixture')
        lock.release()
        self.assertFalse(lock.held)
        with lock:
            self.assertTrue(lock.held)

    def test_reentrant_acquire_rejected_without_losing_lock(self):
        with ServiceInstanceLock(self.path) as lock:
            with self.assertRaises(RuntimeError): lock.acquire()
            self.assertTrue(lock.held)

    def test_busy_failure_closes_its_own_descriptor(self):
        closed = []
        original_close = os.close
        def close(fd): closed.append(fd); original_close(fd)
        with patch.object(module, '_lock_fd', side_effect=OSError(errno.EACCES, 'busy')):
            with patch.object(module.os, 'close', side_effect=close):
                with self.assertRaises(ServiceAlreadyRunning): ServiceInstanceLock(self.path).acquire()
        self.assertEqual(len(closed), 1)

    def test_open_permission_failure_is_not_false_contention(self):
        with patch.object(module.os, 'open', side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError): ServiceInstanceLock(self.path).acquire()

    def test_native_child_contention_then_release(self):
        child = self.worker()
        self.assertEqual(child.stdout.readline().strip(), 'HELD')
        with self.assertRaises(ServiceAlreadyRunning): ServiceInstanceLock(self.path).acquire()
        child.stdin.write('release\n'); child.stdin.flush()
        output, error = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, error)
        self.assertIn('RELEASED', output)
        with ServiceInstanceLock(self.path): pass

    def test_native_exit_without_finally_releases_os_lock(self):
        child = self.worker('exit')
        output, error = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, error)
        self.assertEqual(output.strip(), 'HELD')
        with ServiceInstanceLock(self.path): pass

    def test_native_simultaneous_processes_have_one_winner(self):
        children = [self.worker('race') for _ in range(4)]
        for child in children: child.stdin.write('go\n'); child.stdin.flush()
        states = [child.stdout.readline().strip() for child in children]
        self.assertEqual(states.count('HELD'), 1, states)
        self.assertEqual(states.count('BUSY'), 3, states)


if __name__ == '__main__':
    unittest.main(verbosity=2)
