"""Model contract, recurrent isolation, original PCM and endpoint integration."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as Node
from unittest.mock import patch

import numpy as np

from board.runtime.audio.automatic_capture import SpeechEndpoint
from board.runtime.audio.silero_gate import MODEL_HASHES, SileroFrameGate


class Session:
    def __init__(self):
        self.seen = []
        self.probability = .9
        self.broken = False

    def get_inputs(self):
        return [Node(name=n,shape=s,type='tensor(float)') for n,s in
                [('x',[1,512]),('h',[2,1,64]),('c',[2,1,64])]]

    def get_outputs(self):
        return [Node(name=n) for n in ('prob','new_h','new_c')]

    def run(self, names, values):
        if self.broken:raise RuntimeError('runtime failed')
        self.seen.append({k:v.copy() for k,v in values.items()})
        return np.array([[self.probability]],dtype=np.float32),values['h']+1,values['c']+1


class V5Session(Session):
    def get_inputs(self):
        return [Node(name=n,shape=s,type=t) for n,s,t in
                [('input',[None,None],'tensor(float)'),('state',[2,None,128],'tensor(float)'),('sr',[],'tensor(int64)')]]

    def get_outputs(self):
        return [Node(name=n) for n in ('output','stateN')]

    def run(self,names,values):
        self.seen.append({k:v.copy() for k,v in values.items()})
        return np.array([[self.probability]],dtype=np.float32),values['state']+1


class SileroGateTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.model=Path(temp.name)/'fixture.onnx';self.model.write_bytes(b'contract-fixture')
        self.digest=hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.session=Session()
        self.patch=patch.dict(MODEL_HASHES,{self.digest:'test-only-contract'})
        self.patch.start();self.addCleanup(self.patch.stop)

    def gate(self):
        return SileroFrameGate(self.model,session_factory=lambda path:self.session)

    def test_model_input_windows_are_contiguous_without_overlap(self):
        gate=self.gate();frames=np.arange(320*8,dtype=np.float32)/4000
        for frame in frames.reshape(-1,320):gate(frame)
        joined=np.concatenate([r['x'].reshape(-1) for r in self.session.seen])
        np.testing.assert_array_equal(joined,frames[:len(joined)])
        self.assertEqual(len(joined),2560)
        self.assertEqual(gate.public()['pending_samples'],0)

    def test_incomplete_window_is_not_speech_and_tail_is_bounded(self):
        gate=self.gate();self.assertFalse(gate(np.zeros(320,dtype=np.float32)))
        for _ in range(1000):
            gate(np.zeros(320,dtype=np.float32))
            self.assertLess(gate.public()['pending_samples'],512)

    def test_reset_removes_previous_capture_recurrent_state(self):
        gate=self.gate()
        for _ in range(4):gate(np.ones(320,dtype=np.float32)*.01)
        self.assertGreater(float(gate.h.sum()),0)
        gate.reset();self.assertEqual(float(gate.h.sum()),0)
        self.assertEqual(gate.public()['windows'],0)
        self.assertEqual(gate.public()['pending_samples'],0)
        self.assertFalse(gate(np.zeros(320,dtype=np.float32)))

    def test_different_capture_does_not_share_state(self):
        first=self.gate();second=self.gate()
        first(np.zeros(320,dtype=np.float32));first(np.zeros(320,dtype=np.float32))
        self.assertEqual(float(second.h.sum()),0)
        self.assertEqual(second.public()['pending_samples'],0)

    def test_corrupt_or_wrong_contract_is_rejected(self):
        self.model.write_bytes(b'damaged')
        with self.assertRaises(ValueError):self.gate()

    def test_invalid_probability_and_execution_fail_stop_detector(self):
        for broken,prob in ((True,.5),(False,float('nan')),(False,2.)):
            gate=self.gate();self.session.broken=broken;self.session.probability=prob
            gate(np.zeros(320,dtype=np.float32))
            with self.assertRaises((RuntimeError,ValueError)):gate(np.zeros(320,dtype=np.float32))
            self.assertTrue(gate.public()['failed'])
            with self.assertRaises(RuntimeError):gate(np.zeros(320,dtype=np.float32))

    def test_endpoint_preserves_original_quiet_speech_and_preroll(self):
        gate=self.gate();self.session.probability=0.
        endpoint=SpeechEndpoint(frame_classifier=gate)
        chunks=[];result=None
        for index in range(120):
            # Classifier decision is independent of low input energy.
            self.session.probability=.9 if 25 <= index < 65 else 0.
            frame=(np.arange(320,dtype=np.int16)%17+index).astype('<i2').tobytes()
            chunks.append(frame)
            result=endpoint.feed(frame)
            if result is not None:break
        self.assertIsNotNone(result)
        raw=b''.join(chunks);self.assertEqual(result,raw[-len(result):])
        self.assertLessEqual(endpoint.start_sample,25*320)

    def test_classifier_rejects_loud_noise_without_forcing_energy_fallback(self):
        self.session.probability=0.
        endpoint=SpeechEndpoint(frame_classifier=self.gate())
        for _ in range(150):self.assertIsNone(endpoint.feed(b'\xff\x1f'*320))
        self.assertFalse(endpoint.active)

    def test_v5_context_matches_previous_window_tail(self):
        MODEL_HASHES[self.digest]='silero-v5-k2-release';self.session=V5Session()
        gate=self.gate();frames=np.arange(1280,dtype=np.float32)/2000
        for frame in frames.reshape(-1,320):gate(frame)
        first,second=self.session.seen
        np.testing.assert_array_equal(first['input'][0,:64],np.zeros(64))
        np.testing.assert_array_equal(first['input'][0,64:],frames[:512])
        np.testing.assert_array_equal(second['input'][0,:64],frames[448:512])
        np.testing.assert_array_equal(second['input'][0,64:],frames[512:1024])
        self.assertEqual(int(first['sr']),16000)

    def test_v5_reset_clears_context_and_state(self):
        MODEL_HASHES[self.digest]='silero-v5-k2-release';self.session=V5Session()
        gate=self.gate()
        for _ in range(4):gate(np.ones(320,dtype=np.float32)*.01)
        gate.reset()
        self.assertEqual(float(gate.context.sum()),0.)
        self.assertEqual(float(gate.state.sum()),0.)


if __name__=='__main__':unittest.main()
