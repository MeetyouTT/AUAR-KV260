"""Reconstruct this pinned linear ONNX SFace graph for the VAI PyTorch inspector.

Weights and math are copied exactly. No training or activation replacement.
Only the enumerated, checked ONNX node forms are accepted.
"""
from collections import OrderedDict
import hashlib

import numpy as np
import onnx
from onnx import numpy_helper
import torch
from torch import nn

EXPECTED_SHA = '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'


class SubtractScalar(nn.Module):
    def __init__(self, value):
        super().__init__()
        self.value = float(value)

    def forward(self, value):
        return value-self.value


class MultiplyScalar(nn.Module):
    def __init__(self, value):
        super().__init__()
        self.value = float(value)

    def forward(self, value):
        return value*self.value


def reconstruct(path, *, core_only=False):
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError('This reconstruction only supports the pinned SFace graph')
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    weights = {x.name: numpy_helper.to_array(x).copy() for x in model.graph.initializer}
    layers = OrderedDict()
    previous = 'data'
    rank = 4
    normalization = []
    for node in model.graph.node:
        if len(node.output) != 1 or node.input[0] != previous:
            raise ValueError('Not the expected single-path graph: '+node.name)
        a = {x.name: onnx.helper.get_attribute_value(x) for x in node.attribute}
        w = [weights[n] for n in node.input[1:]]
        op = node.op_type
        if op in ('Sub', 'Mul'):
            if len(w) != 1 or w[0].size != 1:
                raise ValueError('Expected scalar input normalization')
            value = float(w[0].reshape(-1)[0])
            normalization.append({'op': op, 'value': value})
            layer = SubtractScalar(value) if op == 'Sub' else MultiplyScalar(value)
        elif op == 'Conv':
            weight = w[0]
            pads = a.get('pads', [0, 0, 0, 0])
            if pads[:2] != pads[2:] or len(weight.shape) != 4:
                raise ValueError('Unsupported convolution padding/shape')
            groups = a.get('group', 1)
            layer = nn.Conv2d(weight.shape[1]*groups, weight.shape[0], tuple(weight.shape[2:]),
                stride=tuple(a.get('strides', [1, 1])), padding=tuple(pads[:2]),
                dilation=tuple(a.get('dilations', [1, 1])), groups=groups, bias=len(w) == 2)
            layer.weight.data.copy_(torch.from_numpy(weight))
            if len(w) == 2:
                layer.bias.data.copy_(torch.from_numpy(w[1]))
        elif op == 'BatchNormalization':
            cls = nn.BatchNorm2d if rank == 4 else nn.BatchNorm1d
            layer = cls(len(w[0]), eps=a.get('epsilon', 1e-5))
            for name, value in zip(['weight', 'bias', 'running_mean', 'running_var'], w):
                getattr(layer, name).data.copy_(torch.from_numpy(value))
        elif op == 'PRelu':
            if w[0].shape != (len(w[0]), 1, 1):
                raise ValueError('Expected per-channel PReLU')
            layer = nn.PReLU(len(w[0]))
            layer.weight.data.copy_(torch.from_numpy(w[0].reshape(-1)))
        elif op == 'Dropout':
            layer = nn.Dropout(float(a.get('ratio', .5)))
        elif op == 'Flatten':
            if a.get('axis', 1) != 1:
                raise ValueError('Unexpected flatten axis')
            layer = nn.Flatten(1)
            rank = 2
        elif op == 'Gemm':
            if a.get('transA', 0) != 0 or a.get('transB', 0) != 1 or a.get('alpha', 1) != 1 or a.get('beta', 1) != 1:
                raise ValueError('Unexpected fully connected convention')
            layer = nn.Linear(w[0].shape[1], w[0].shape[0], bias=len(w) == 2)
            layer.weight.data.copy_(torch.from_numpy(w[0]))
            if len(w) == 2:
                layer.bias.data.copy_(torch.from_numpy(w[1]))
        else:
            raise ValueError('Unexpected SFace operator: '+op)
        if not (core_only and op in ('Sub', 'Mul')):
            layers[node.name] = layer
        previous = node.output[0]
    if previous != 'fc1' or normalization != [{'op': 'Sub', 'value': 127.5}, {'op': 'Mul', 'value': .0078125}]:
        raise ValueError('Unexpected SFace outputs or normalization')
    return nn.Sequential(layers).eval(), normalization


def verify(model, fixture):
    checks = []
    with torch.no_grad():
        for name in fixture['names']:
            source = fixture['input_'+str(name)]
            reference = fixture['output_'+str(name)].reshape(-1).astype(np.float64)
            value = model(torch.from_numpy(source)).numpy().reshape(-1).astype(np.float64)
            cosine = float(np.dot(value, reference)/(np.linalg.norm(value)*np.linalg.norm(reference)))
            error = float(np.max(np.abs(value-reference)))
            if value.shape != (128,) or not np.isfinite(value).all() or cosine < .99999 or error > .01:
                raise ValueError('Reconstruction parity failed: '+str(name)+': '+str((cosine, error)))
            checks.append({'sample': str(name), 'cosine': cosine, 'maximum_absolute_error': error})
    return checks
