"""Second equivalent rewrite: residual PReLU and grouped spatial FC, no slices."""
from collections import OrderedDict
import copy
import torch
from torch import nn


class ResidualPRelu(nn.Module):
    """PReLU(x,a) = x + (1-a)*ReLU(-x), preserving each learned slope."""
    def __init__(self, original):
        super().__init__()
        channels = original.weight.numel()
        self.negative = nn.Conv2d(channels, channels, 1, groups=channels, bias=False)
        self.relu = nn.ReLU()
        self.slope = nn.Conv2d(channels, channels, 1, groups=channels, bias=False)
        self.negative.weight.data.fill_(-1.)
        self.slope.weight.data.copy_(1-original.weight.detach().reshape(channels, 1, 1, 1))

    def forward(self, value):
        return value+self.slope(self.relu(self.negative(value)))


class GroupedSpatialFullyConnected(nn.Module):
    """Two channel-partitioned sums, expressed without runtime input slicing."""
    def __init__(self, original):
        super().__init__()
        if (original.in_features, original.out_features) != (50176, 128):
            raise ValueError('Unexpected SFace head shape')
        self.partition = nn.Conv2d(1024, 256, 7, groups=2, bias=True)
        self.sum = nn.Conv2d(256, 128, 1, bias=False)
        weight = original.weight.detach().reshape(128, 1024, 7, 7)
        self.partition.weight.data.copy_(torch.cat((weight[:, :512], weight[:, 512:]), dim=0))
        self.partition.bias.data.copy_(torch.cat((original.bias.detach(), torch.zeros(128)), dim=0))
        self.sum.weight.data.copy_(torch.cat((torch.eye(128), torch.eye(128)), dim=1).reshape(128, 256, 1, 1))

    def forward(self, value):
        return self.sum(self.partition(value))


def rewrite(core):
    torch.manual_seed(20261018)
    layers = OrderedDict()
    counts = {'residual_prelu': 0, 'grouped_spatial_fc': 0, 'removed_flatten': 0, 'spatial_output_bn': 0}
    for name, source in core.named_children():
        if isinstance(source, nn.PReLU):
            layer = ResidualPRelu(source)
            probe = torch.randn(1, source.weight.numel(), 3, 3)
            with torch.no_grad():
                if not torch.allclose(layer(probe), source(probe), atol=1e-6, rtol=1e-5):
                    raise ValueError('Residual activation parity failed')
            counts['residual_prelu'] += 1
        elif isinstance(source, nn.Flatten):
            counts['removed_flatten'] += 1
            continue
        elif isinstance(source, nn.Linear):
            layer = GroupedSpatialFullyConnected(source)
            probe = torch.randn(1, 1024, 7, 7)
            with torch.no_grad():
                if not torch.allclose(layer(probe).reshape(1, 128), source(probe.reshape(1, -1)), atol=1e-4, rtol=1e-4):
                    raise ValueError('Grouped head parity failed')
            counts['grouped_spatial_fc'] += 1
        elif isinstance(source, nn.BatchNorm1d):
            layer = nn.BatchNorm2d(source.num_features, eps=source.eps)
            layer.load_state_dict(source.state_dict())
            counts['spatial_output_bn'] += 1
        else:
            layer = copy.deepcopy(source)
        layers[name] = layer
    layers['output_flatten'] = nn.Flatten(1)
    if counts != {'residual_prelu': 27, 'grouped_spatial_fc': 1, 'removed_flatten': 1, 'spatial_output_bn': 1}:
        raise ValueError('Unexpected SFace v2 rewrite coverage')
    return nn.Sequential(layers).eval(), counts
