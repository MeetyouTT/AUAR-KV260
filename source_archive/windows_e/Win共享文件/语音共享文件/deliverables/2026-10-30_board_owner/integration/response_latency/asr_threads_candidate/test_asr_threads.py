"""No models or devices; injected recognizer factory and public tiny fixtures."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
PATH=ROOT/'after/board/runtime/audio/board_asr.py'
spec=importlib.util.spec_from_file_location('asr_three_thread_candidate',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ThreadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.calls=[]
        self.content={'model.int8.onnx':b'public fake model fixture','tokens.txt':b'public fake token fixture'}
        for name,data in self.content.items():(self.root/name).write_bytes(data)
        self.hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in self.content.items()}
    def factory(self,**kwargs):self.calls.append(kwargs);return object()
    def make(self,**kwargs):
        return module.BoardParaformer(self.root,model_sha256=self.hashes['model.int8.onnx'],
            tokens_sha256=self.hashes['tokens.txt'],recognizer_factory=self.factory,**kwargs)
    def test_default_is_two_and_original_recognizer_parameters_remain(self):
        value=self.make()
        self.assertEqual(self.calls,[dict(paraformer=str(self.root/'model.int8.onnx'),tokens=str(self.root/'tokens.txt'),
            num_threads=2,sample_rate=16000,feature_dim=80,decoding_method='greedy_search',provider='cpu')])
        self.assertEqual(value.model_sha256,self.hashes['model.int8.onnx'])
        self.assertEqual(value.tokens_sha256,self.hashes['tokens.txt'])
        self.assertEqual(value.MAX_SAMPLES,320000)
    def test_one_two_three_are_passed_without_coercion(self):
        for count in (1,2,3):
            with self.subTest(count=count):
                self.make(num_threads=count);self.assertEqual(self.calls[-1]['num_threads'],count)
    def test_invalid_counts_rejected_before_any_factory(self):
        for count in (True,False,0,4,5,100,-1,1.,3.,None,'3'):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):self.make(num_threads=count)
        self.assertEqual(self.calls,[])
    def test_original_resource_hash_gate_still_precedes_factory(self):
        for name in self.content:
            with self.subTest(name=name):
                (self.root/name).write_bytes(b'changed public fixture')
                with self.assertRaises(module.BoardAsrUnavailable):self.make(num_threads=3)
                (self.root/name).write_bytes(self.content[name])
        self.assertEqual(self.calls,[])
    def test_only_exact_two_guard_strings_changed_and_python39(self):
        before=(ROOT.parent/'source_before/board/runtime/audio/board_asr.py').read_bytes()
        after=PATH.read_bytes()
        restored=after.replace(b'not 1 <= num_threads <= 3:',b'not 1 <= num_threads <= 2:',1)
        restored=restored.replace(b'Use one to three board ASR threads',b'Use one or two board ASR threads',1)
        self.assertEqual(restored,before)
        ast.parse(after.decode('utf-8'),feature_version=(3,9))

if __name__=='__main__':unittest.main()
