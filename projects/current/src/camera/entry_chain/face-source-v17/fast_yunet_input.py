"""Bit-equivalent input encoding for the reviewed uint8 BGR -> blob path.

Only native YuNet with fix7 / [1,320,320,3] is eligible. Admission, ownership,
model execution, output conversion and face decode/NMS remain with their
original implementations. This module itself opens no model or device.
"""
import numpy as np


def encode_blob_integer_nhwc(blob):
    if not isinstance(blob,np.ndarray) or blob.dtype!=np.float32 or blob.shape!=(1,3,320,320):
        raise ValueError('Fast YuNet requires float32 [1,3,320,320] integer BGR blob')
    low,high=blob.min(),blob.max()
    if not (np.isfinite(low) and np.isfinite(high) and 0<=low and high<=255):
        raise ValueError('Fast YuNet blob must be finite and within 0..255')
    integer=blob.astype(np.uint16)
    if not np.array_equal(blob,integer):
        raise ValueError('Fast YuNet only supports original uint8-derived integer samples')
    integer+=np.uint16(1)
    np.right_shift(integer,1,out=integer)
    np.minimum(integer,127,out=integer)
    return np.ascontiguousarray(integer.transpose(0,2,3,1),dtype=np.int8)


def _direct(name,function,*args,**kwargs):return function(*args,**kwargs)


def eligible(adapter):
    if getattr(adapter,'native_critical',False) is not True:return False
    runner=getattr(adapter,'runner',None)
    if runner is None or getattr(runner,'input_fix',None)!=7:return False
    inputs=getattr(runner,'inputs',())
    return (len(inputs)==1 and list(getattr(inputs[0],'dims',()))==[1,320,320,3]
            and hasattr(getattr(adapter,'detector',None),'net'))


class FastYuNetNetwork:
    def __init__(self,adapter,output_transform,measure=None):
        if not eligible(adapter):raise ValueError('Unsupported native YuNet input contract')
        if not callable(output_transform) or (measure is not None and not callable(measure)):
            raise ValueError('Output transform and optional measurement must be callable')
        self.adapter,self.runner=adapter,adapter.runner
        self.output_transform=output_transform;self.measure=measure or _direct;self.source=None
    def setInput(self,blob):
        self.source=None
        self.source=self.measure('fast_input_encode',encode_blob_integer_nhwc,blob)
    def forward(self,names):return self.measure('fast_network_forward',self._forward,names)
    def _forward(self,names):
        if names!=['loc','conf','iou']:raise ValueError('Unsupported YuNet CPU outputs')
        if self.source is None:raise ValueError('Fast YuNet requires a valid current setInput')
        guard=getattr(self.adapter,'_admission_check',None)
        if guard is None:raise ValueError('Native YuNet requires the source frame admission guard')
        result=self.adapter._native_scheduled(self.source,guard)
        if result is None:
            from board.vision.dpu_vision_runtime import SlotUnavailable
            raise SlotUnavailable('Face detection skipped for a primary DPU deadline')
        return self.output_transform(result)


def install(adapter_type,output_transform,measure=None):
    if not callable(output_transform) or (measure is not None and not callable(measure)):
        raise ValueError('Output transform and optional measurement must be callable')
    if getattr(adapter_type,'_aura_fast_yunet_input_v16',False):return
    original=adapter_type.__init__
    def initialize(self,*args,**kwargs):
        original(self,*args,**kwargs)
        if eligible(self):self.detector.net=FastYuNetNetwork(self,output_transform,measure)
    adapter_type.__init__=initialize
    adapter_type._aura_fast_yunet_input_v16=True
