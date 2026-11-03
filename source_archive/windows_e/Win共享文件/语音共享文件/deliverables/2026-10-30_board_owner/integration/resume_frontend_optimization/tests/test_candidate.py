"""Synthetic recurrent session/boundary/quantization tests, no real models."""
import ctypes
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0,str(PROJECT/'aura'))
import board.runtime.audio.board_gtcrn_fft as baseline


def candidate_module():
    p = Path(__file__).resolve().parents[1]/'candidate/board_gtcrn_reuse.py'
    spec = importlib.util.spec_from_file_location('isolated_gtcrn_reuse',p)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class Binding:
    def __init__(self):
        self.inputs,self.outputs = {},{}
    def bind_cpu_input(self,name,value):
        self.inputs[name] = value
    def bind_output(self,name,*,device_type,device_id,element_type,shape,buffer_ptr):
        assert device_type == 'cpu' and device_id == 0 and element_type == np.float32
        raw = (ctypes.c_float*math.prod(shape)).from_address(buffer_ptr)
        self.outputs[name] = np.ctypeslib.as_array(raw).reshape(shape)


class Session:
    def __init__(self,*args,**kwargs):
        self.trace,self.bindings = [],[]
    def get_modelmeta(self):
        return SimpleNamespace(custom_metadata_map=dict(model_type='gtcrn',n_fft='512',hop_length='256',
            window_length='512',sample_rate='16000',window_type='hann_sqrt',
            conv_cache_shape='1,2',tra_cache_shape='1,2',inter_cache_shape='1,2'))
    def get_inputs(self):
        return [SimpleNamespace(name=n) for n in ('mix','conv_cache','tra_cache','inter_cache')]
    def get_outputs(self):
        return [SimpleNamespace(name=n,shape=(1,257,1,2) if i == 0 else (1,2),type='tensor(float)')
            for i,n in enumerate(('enh','conv_cache_out','tra_cache_out','inter_cache_out'))]
    def run(self,names,feed):
        states = [feed[n] for n in ('conv_cache','tra_cache','inter_cache')]
        self.trace.append(tuple(float(x.flat[0]) for x in states))
        enhanced = feed['mix']*np.float32(.97)+np.float32(sum(x.flat[0] for x in states)*1e-6)
        return [enhanced]+[x+np.float32(i+1) for i,x in enumerate(states)]
    def io_binding(self):
        value = Binding()
        self.bindings.append(value)
        return value
    def run_with_iobinding(self,binding):
        for inp in list(binding.inputs.values())[1:]:
            for out in list(binding.outputs.values())[1:]:
                assert not np.shares_memory(inp,out),'Recurrent state input and output must not alias'
        values = self.run(list(binding.outputs),binding.inputs)
        for target,value in zip(binding.outputs.values(),values):
            np.copyto(target,value)


@pytest.fixture
def resources(tmp_path,monkeypatch):
    model = tmp_path/'synthetic-gtcrn.onnx'
    model.write_bytes(b'Synthetic session only; not ONNX')
    hashes = dict(baseline.HASHES)
    hashes['gtcrn_simple.onnx'] = hashlib.sha256(model.read_bytes()).hexdigest()
    monkeypatch.setattr(baseline,'HASHES',hashes)
    return model


@pytest.mark.parametrize('length',[0,1,255,256,257,319,320,512,1001])
@pytest.mark.parametrize('reuse,binding',[(True,False),(False,True),(True,True)])
def test_streamed_lengths_values_state_order_and_flush_match_baseline(resources,length,reuse,binding):
    module = candidate_module()
    reference = baseline.FftGtcrnDenoiser(resources,session_factory=Session)
    actual = module.ReuseFftGtcrnDenoiser(resources,session_factory=Session,
        buffer_reuse=reuse,io_binding=binding)
    audio = np.random.default_rng(27).normal(0,.03,length).astype(np.float32)
    a,b = [],[]
    for pos in range(0,length,73):
        x,y = reference(audio[pos:pos+73]).samples,actual(audio[pos:pos+73]).samples
        assert len(x) == len(y)
        a.append(x);b.append(y)
    a.append(reference.flush().samples);b.append(actual.flush().samples)
    a,b = np.concatenate(a),np.concatenate(b)
    assert len(a) == len(b) == length
    np.testing.assert_array_equal(a,b)
    assert reference.session.trace == actual.session.trace
    assert actual.total_input == actual.total_output == 0
    assert actual.session.trace == [(float(i),float(i*2),float(i*3)) for i in range(len(actual.session.trace))]


def test_reset_removes_old_recurrent_state_and_bound_outputs(resources):
    module = candidate_module()
    value = module.ReuseFftGtcrnDenoiser(resources,session_factory=Session,io_binding=True)
    first = value(np.ones(320,dtype=np.float32)*.01).samples.copy()
    value(np.ones(320,dtype=np.float32)*.02)
    value.reset()
    again = value(np.ones(320,dtype=np.float32)*.01).samples
    np.testing.assert_array_equal(first,again)
    assert value.session.trace[-1] == (0.,0.,0.)


def test_explicit_missing_binding_rejects_instead_of_silent_fallback(resources):
    module = candidate_module()
    class Missing(Session):
        io_binding = None
    with pytest.raises(ValueError,match='unavailable'):
        module.ReuseFftGtcrnDenoiser(resources,session_factory=Missing,io_binding=True)


def test_quantized_frame_buffer_is_bit_identical_to_original_pcm16_roundtrip():
    module = candidate_module()
    frame = np.random.default_rng(64).uniform(-1,1,320).astype(np.float32)
    frame[:8] = [0.,-0.,-1e-12,1e-12,-1.,1.,.5/32768,-.5/32768]
    def configure(cls):
        gate = cls.__new__(cls)
        gate.np,gate.clock,gate.lock = np,lambda:1.,threading.Lock()
        gate.closed,gate.error,gate.frames,gate.samples,gate.last_ms,gate.max_ms = False,'',0,0,None,0.
        gate.buffer_reuse = True
        gate._quantized = np.empty(320,dtype=np.float32)
        seen = []
        def denoise(values,rate):
            seen.append(values.copy())
            return SimpleNamespace(samples=values.copy())
        gate.denoiser = denoise
        gate.vad = SimpleNamespace(accept_waveform=lambda x:None,is_speech_detected=lambda:False,
                                  empty=lambda:True)
        return gate,seen
    original,expected = configure(baseline.BoardFftSpeechGate)
    actual,received = configure(module.ReuseFftSpeechGate)
    assert original(frame) == actual(frame) == False
    np.testing.assert_array_equal(expected[0].view(np.uint32),received[0].view(np.uint32))
    assert original.samples == actual.samples == 320


def test_source_pin_rejects_unreviewed_baseline(tmp_path,monkeypatch):
    module = candidate_module()
    other = tmp_path/'unreviewed.py'
    other.write_text('unreviewed',encoding='utf-8')
    monkeypatch.setattr(baseline,'__file__',str(other))
    with pytest.raises(ValueError,match='baseline'):
        module.verify_baseline()
