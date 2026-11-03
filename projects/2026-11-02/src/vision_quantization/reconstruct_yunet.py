"""Exact pinned YuNet CNN, with shape operations and Softmax left to CPU."""
from collections import Counter
import hashlib
from pathlib import Path
import onnx
from onnx import numpy_helper
import torch
from torch import nn
import numpy as np

SHA256 = '50ef07f702a31741ca46a4c0d947773b64143b9362780237bf0d427d6c79bab7'
HEADS = ('242', '249', '256', '263')


class YuNetCore(nn.Module):
    def __init__(self, nodes, layers):
        super().__init__()
        self.layers = nn.ModuleList(layers)
        self.edges = [(node.input[0], node.output[0]) for node in nodes]

    def forward(self, value):
        values = {'input': value}
        for layer, (source, target) in zip(self.layers, self.edges):
            values[target] = layer(values[source])
        return values['242'], values['249'], values['256'], values['263']


def reconstruct(path):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Only the pinned YuNet 2022mar model is supported')
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    weights = {x.name: numpy_helper.to_array(x).copy() for x in model.graph.initializer}
    nodes = [n for n in model.graph.node if n.op_type in ('Conv', 'Relu', 'MaxPool')]
    if Counter(n.op_type for n in nodes) != {'Conv': 43, 'Relu': 18, 'MaxPool': 5}:
        raise ValueError('Unexpected YuNet CNN coverage')
    layers = []
    for node in nodes:
        a = {x.name: onnx.helper.get_attribute_value(x) for x in node.attribute}
        if node.op_type == 'Conv':
            w = weights[node.input[1]]
            pads = a['pads']
            if pads[:2] != pads[2:]:
                raise ValueError('Asymmetric convolution padding')
            groups = a['group']
            layer = nn.Conv2d(w.shape[1] * groups, w.shape[0], tuple(w.shape[2:]),
                              stride=tuple(a['strides']), padding=tuple(pads[:2]),
                              dilation=tuple(a['dilations']), groups=groups, bias=True)
            # Host input is BGR / 256. Fold its inverse into the first weight.
            factor = 256. if node.input[0] == 'input' else 1.
            layer.weight.data.copy_(torch.from_numpy(w * factor))
            layer.bias.data.copy_(torch.from_numpy(weights[node.input[2]]))
        elif node.op_type == 'Relu':
            layer = nn.ReLU()
        else:
            if a['pads'] != [0, 0, 0, 0] or a.get('ceil_mode', 0) != 0:
                raise ValueError('Unexpected pooling parameters')
            layer = nn.MaxPool2d(tuple(a['kernel_shape']), tuple(a['strides']))
        layers.append(layer)
    return YuNetCore(nodes, layers).eval()


def cpu_outputs(heads):
    """Accept four NCHW arrays, return the original loc/conf/iou CPU layout."""
    rows = np.concatenate([np.transpose(h, (0, 2, 3, 1)).reshape(h.shape[0], -1)
                           for h in heads], axis=1).reshape(-1, 17)
    logits = rows[:, 14:16]
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return rows[:, :14].copy(), e / e.sum(axis=1, keepdims=True), rows[:, 16:17].copy()
