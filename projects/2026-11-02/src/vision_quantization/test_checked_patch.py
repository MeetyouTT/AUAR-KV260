import copy
import random
import unittest
from make_checked_patch import make_patch, apply_patch


class PatchTests(unittest.TestCase):
    def setUp(self):
        rng = random.Random(260)
        self.base = bytes(rng.randrange(256) for _ in range(8192))
        self.result = self.base[4096:] + b'changed-header' + self.base[:4096]

    def test_reordered_weights_and_inserted_metadata_reconstruct_exactly(self):
        patch, copied = make_patch(self.base, self.result)
        self.assertGreater(copied, 7000)
        self.assertEqual(apply_patch(self.base, patch), self.result)

    def test_wrong_base_cannot_produce_a_model(self):
        patch, _ = make_patch(self.base, self.result)
        with self.assertRaises(ValueError):
            apply_patch(b'bad' + self.base[3:], patch)

    def test_out_of_bounds_copy_is_rejected(self):
        patch, _ = make_patch(self.base, self.result)
        bad = copy.deepcopy(patch)
        index = next(i for i, x in enumerate(bad['operations']) if x[0] == 'copy')
        bad['operations'][index][1] = -1
        with self.assertRaises(ValueError):
            apply_patch(self.base, bad)


if __name__ == '__main__':
    unittest.main()
