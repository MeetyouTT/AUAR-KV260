import os
from types import SimpleNamespace
import unittest

from inspect_board_context import lock_holders


class LockObservationTests(unittest.TestCase):
    def setUp(self):
        self.stat = SimpleNamespace(st_dev=os.makedev(0, 20), st_ino=345)

    def test_existing_flock_owner(self):
        self.assertEqual(lock_holders(self.stat, '1: FLOCK ADVISORY WRITE 123 00:14:345 0 EOF'),
                         [{'type': 'FLOCK', 'mode': 'WRITE', 'pid': 123}])

    def test_waiter_is_not_owner(self):
        self.assertEqual(lock_holders(self.stat, '1: -> FLOCK ADVISORY WRITE 789 00:14:345 0 EOF'), [])

    def test_other_inode_not_included(self):
        self.assertEqual(lock_holders(self.stat, '1: FLOCK ADVISORY WRITE 123 00:14:346 0 EOF'), [])

    def test_other_device_not_included(self):
        self.assertEqual(lock_holders(self.stat, '1: FLOCK ADVISORY WRITE 123 00:15:345 0 EOF'), [])

    def test_empty_locks_is_not_permission(self):
        self.assertEqual(lock_holders(self.stat, ''), [])


if __name__ == '__main__':
    unittest.main()
