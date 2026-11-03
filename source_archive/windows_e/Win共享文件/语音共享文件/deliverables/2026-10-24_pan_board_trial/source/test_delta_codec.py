import copy
import unittest
from delta_codec import apply_delta, digest, make_delta


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.base = bytes(range(256)) * 64
        self.target = self.base[:4500] + b'changed data' + self.base[4550:] + b'tail'
        self.patch, _ = make_delta(self.base, self.target)

    def test_insert_delete_and_tail_roundtrip(self):
        self.assertEqual(apply_delta(self.base, self.patch, digest(self.target)), self.target)

    def test_wrong_base_rejected(self):
        with self.assertRaises(ValueError):apply_delta(b'bad', self.patch, digest(self.target))

    def test_wrong_approved_target_rejected(self):
        with self.assertRaises(ValueError):apply_delta(self.base, self.patch, '0' * 64)

    def test_copy_outside_base_rejected(self):
        patch = copy.deepcopy(self.patch);patch['ops'] = [['copy', len(self.base), 20]]
        with self.assertRaises(ValueError):apply_delta(self.base, patch, digest(self.target))

    def test_incomplete_target_rejected(self):
        patch = copy.deepcopy(self.patch);patch['ops'] = patch['ops'][:-1]
        with self.assertRaises(ValueError):apply_delta(self.base, patch, digest(self.target))


if __name__ == '__main__':unittest.main()
