"""Numerical boundary checks for exact rewrites, separate from calibration."""
import unittest
import torch
from torch import nn
from rewrite_sface_v2 import ResidualPRelu, GroupedSpatialFullyConnected


class RewriteTests(unittest.TestCase):
    def test_prelu_zero_negative_large_and_channel_specific_slopes(self):
        source = nn.PReLU(6)
        source.weight.data.copy_(torch.tensor([-2., -.5, 0., .5, 1., 2.]))
        value = torch.tensor([-1000., -1., -1e-6, 0., 1e-6, 1., 1000.]).reshape(1, 1, 1, 7).repeat(1, 6, 1, 1)
        candidate = ResidualPRelu(source)
        torch.testing.assert_close(candidate(value), source(value), atol=1e-5, rtol=1e-5)

    def test_head_channel_and_spatial_partition_order(self):
        torch.manual_seed(91)
        source = nn.Linear(50176, 128)
        candidate = GroupedSpatialFullyConnected(source)
        for index in [0, 48, 49, 511*49+48, 512*49, 50175]:
            value = torch.zeros(1, 1024, 7, 7)
            value.reshape(-1)[index] = 1.
            torch.testing.assert_close(candidate(value).reshape(1, 128), source(value.reshape(1, -1)),
                                       atol=1e-6, rtol=1e-5)

    def test_head_random_inputs_and_bias(self):
        torch.manual_seed(92)
        source = nn.Linear(50176, 128)
        source.bias.data.copy_(torch.linspace(-2, 2, 128))
        value = torch.randn(2, 1024, 7, 7)
        candidate = GroupedSpatialFullyConnected(source)
        torch.testing.assert_close(candidate(value).reshape(2, 128), source(value.reshape(2, -1)),
                                   atol=1e-4, rtol=1e-4)


if __name__ == '__main__':
    torch.set_num_threads(2)
    unittest.main(verbosity=2)
