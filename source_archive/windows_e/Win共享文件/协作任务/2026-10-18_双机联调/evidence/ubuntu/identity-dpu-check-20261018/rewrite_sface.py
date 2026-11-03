"""Exact FP32 graph rewrite experiments, not a production quantized model."""
from collections import OrderedDict
import copy

import torch
from torch import nn


class PReluAsConvolutions(nn.Module):
    """PReLU(x,a) = ReLU(x) + (-a)*ReLU((-1)*x), per channel."""
    def __init__(self, original):
        super().__init__()
        channels = original.weight.numel()
        self.positive = nn.ReLU()
        self.negative = nn.Conv2d(channels, channels, 1, groups=channels, bias=False)
        self.negative_relu = nn.ReLU()
        self.slope = nn.Conv2d(channels, channels, 1, groups=channels, bias=False)
        self.negative.weight.data.fill_(-1.)
        self.slope.weight.data.copy_(-original.weight.detach().reshape(channels, 1, 1, 1))

    def forward(self, value):
        return self.positive(value)+self.slope(self.negative_relu(self.negative(value)))


class SplitSpatialFullyConnected(nn.Module):
    """Partition 7x7x1024 -> 128 weights across two 512-channel convolutions."""
    def __init__(self, original):
        super().__init__()
        if original.in_features != 1024*7*7 or original.out_features != 128:
            raise ValueError('Unexpected SFace fully connected shape')
        self.left = nn.Conv2d(512, 128, 7, bias=True)
        self.right = nn.Conv2d(512, 128, 7, bias=False)
        weights = original.weight.detach().reshape(128, 1024, 7, 7)
        self.left.weight.data.copy_(weights[:, :512])
        self.right.weight.data.copy_(weights[:, 512:])
        self.left.bias.data.copy_(original.bias.detach())

    def forward(self, value):
        image = value.reshape(-1, 1024, 7, 7)
        return (self.left(image[:, :512])+self.right(image[:, 512:])).reshape(-1, 128)


def rewrite(core):
    layers = OrderedDict()
    counts = {'prelu_rewritten': 0, 'fully_connected_split': 0}
    torch.manual_seed(20261018)
    for name, source in core.named_children():
        if isinstance(source, nn.PReLU):
            layer = PReluAsConvolutions(source)
            probe = torch.randn(1, source.weight.numel(), 2, 2)
            with torch.no_grad():
                if not torch.allclose(layer(probe), source(probe), atol=1e-6, rtol=1e-6):
                    raise ValueError('PReLU rewrite parity failed: '+name)
            counts['prelu_rewritten'] += 1
        elif isinstance(source, nn.Linear):
            layer = SplitSpatialFullyConnected(source)
            probe = torch.randn(1, source.in_features)
            with torch.no_grad():
                if not torch.allclose(layer(probe), source(probe), atol=1e-4, rtol=1e-4):
                    raise ValueError('Split fully connected parity failed')
            counts['fully_connected_split'] += 1
        else:
            layer = copy.deepcopy(source)
        layers[name] = layer
    if counts != {'prelu_rewritten': 27, 'fully_connected_split': 1}:
        raise ValueError('Unexpected graph rewrite coverage')
    return nn.Sequential(layers).eval(), counts
