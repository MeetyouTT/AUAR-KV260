"""Binding contracts against a fake C ABI: no DSO/model/device is loaded."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import native_binding as b


class Function:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class Owner:
    fingerprint = b.FINGERPRINT

    def __init__(self, path):
        self.config = {'native_library': str(path), 'native_sha256': sha(path)}
        self.ownership = path.open('rb')
        self.handle = 771
        self.lock = threading.Lock()
        self.destroyed = []

    def close(self):
        with self.lock:
            if self.handle:
                self.destroyed.append(self.handle)
                self.handle = None
            if self.ownership:
                self.ownership.close()
                self.ownership = None


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class FakeABI:
    def __init__(self):
        self.adopted = False
        self.destroyed = 0
        self.closed = False
        self.models = set()
        self.execute_calls = 0
        self.create_calls = 0
        self.hardcap = self.guard = False
        self.unknown = self.denied = False
        self.adopt_mode = 'success'
        self.output_fix = 5
        self.bad_report = False
        self.inputs = {'name': 'sface_input', 'dims': [1, 112, 112, 3], 'dtype': 'xint8', 'fix_point': 7}
        self.outputs = {'name': 'sface_output', 'dims': [1, 128], 'dtype': 'xint8', 'fix_point': 5}
        for name in ('abi', 'report_size', 'state_size', 'error', 'context_create', 'context_close',
                     'adopt_yolo', 'snapshot', 'announce_primary', 'runner_create', 'runner_close',
                     'tensor_info', 'optional_execute', 'yolo_execute'):
            setattr(self, 'aura_native_' + name, Function(getattr(self, name)))

    def abi(self): return 1
    def report_size(self): return C.sizeof(b.Report)
    def state_size(self): return C.sizeof(b.State)
    def error(self): return b'injected fake native error'

    def context_create(self, fd, path):
        self.create_calls += 1
        return 31

    def context_close(self, cid):
        if self.models or self.unknown:
            return -1
        self.closed = True
        self.destroyed += int(self.adopted)
        self.adopted = False
        return 0

    def adopt_yolo(self, cid, handle):
        if self.adopt_mode == 'reject': return -1
        if self.adopt_mode == 'interrupt_before': raise KeyboardInterrupt()
        self.adopted = True
        if self.adopt_mode == 'interrupt_after': raise KeyboardInterrupt()
        return 0

    def snapshot(self, cid, pointer):
        state = pointer._obj
        state.abi_version = 1
        state.fenced = self.unknown
        state.admissions[2] = self.execute_calls
        return 0

    def announce_primary(self, cid, deadline): return 0

    def runner_create(self, cid, task, model):
        self.models.add(41)
        return 41

    def runner_close(self, cid, mid):
        if self.unknown: return -1
        self.models.remove(mid)
        return 0

    def tensor_info(self, cid, mid, output, index, pointer):
        item = self.outputs if output else self.inputs
        info = pointer._obj
        info.rank = len(item['dims'])
        size = 1
        for i, value in enumerate(item['dims']):
            info.dims[i] = value
            size *= value
        info.bytes = size
        info.fix_point = self.output_fix if output else item['fix_point']
        info.name = item['name'].encode()
        return 0

    def fill(self, pointer, task):
        report = pointer._obj
        report.abi_version = 2 if self.bad_report else 1
        report.task = task
        report.outcome = 5 if self.unknown else 1 if self.denied else 0
        report.hardcap, report.guard = self.hardcap, self.guard
        report.submitted = not self.denied
        report.completed = not self.unknown and not self.denied
        report.native_status = -1 if self.unknown or self.denied else 0
        if not self.denied:
            report.start_ns = 10
            report.native_return_ns = 20
            report.release_decision_ns = 21
            report.after_unlock_ns = 22

    def optional_execute(self, cid, mid, source, size, ports, count, expires, report):
        self.execute_calls += 1
        self.fill(report, 2)
        if self.unknown: return -2
        if self.denied: return 1
        C.memset(ports[0].data, 42, ports[0].bytes)
        return 0

    def yolo_execute(self, cid, bgr, width, height, stride, output, capacity,
                     class_id, count, expires, finish, report):
        self.execute_calls += 1
        self.fill(report, 0)
        if self.unknown: return -2
        if self.denied: return 1
        count._obj.value = 1
        for i, value in enumerate((1, 2, 3, 4, .9, 0)):
            output[i] = value
        return 0


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / 'candidate.so'
        self.library.write_bytes(b'not an ELF; CDLL is mocked')
        self.owner = Owner(self.library)
        self.fake = FakeABI()
        self.mock = patch.object(b.C, 'CDLL', return_value=self.fake)
        self.mock.start()
        self.addCleanup(self.mock.stop)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.owner.close)
        self.model = self.root / 'model.xmodel'
        self.model.write_bytes(b'not a model; native factory is mocked')
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'sha256': sha(self.model), 'partitions': [{
            'device': 'DPU', 'fingerprint': b.FINGERPRINT,
            'inputs': [self.fake.inputs], 'outputs': [self.fake.outputs]}]}))

    def context(self):
        return b.NativeContext(self.owner, self.library, sha(self.library))

    def runner(self, context):
        if not context.adopted:
            context.adopt_yolo()
        return b.NativeRunner(context, 'sface', self.model, sha(self.model), self.manifest, sha(self.manifest))

    def source(self): return bytes(112 * 112 * 3)
    def expires(self): return time.monotonic_ns() + 1_000_000_000

    def test_pin_refusal_precedes_loading(self):
        with self.assertRaises(ValueError):
            b.NativeContext(self.owner, self.library, '0' * 64)
        self.assertEqual(self.fake.create_calls, 0)

    def test_abi_size_refusal_precedes_factory(self):
        self.fake.aura_native_report_size.callback = lambda: 63
        with self.assertRaises(b.BridgeError): self.context()
        self.assertEqual(self.fake.create_calls, 0)

    def test_success_metadata_and_exact_bytes(self):
        ctx = self.context(); runner = self.runner(ctx)
        result = runner.execute_encoded(self.source(), source_expires_ns=self.expires())
        self.assertTrue(result.usable)
        self.assertEqual(result.outputs, (b'*' * 128,))
        self.assertEqual(ctx.snapshot()['admissions'][2], 1)
        runner.close(); ctx.close()

    def test_wrong_tensor_quantization_closes_unused_model(self):
        ctx = self.context(); self.fake.output_fix = 4
        with self.assertRaises(ValueError): self.runner(ctx)
        self.assertFalse(ctx.models)
        self.assertFalse(self.fake.models)

    def test_input_byte_count_and_monotonic_deadline_refused(self):
        ctx = self.context(); runner = self.runner(ctx)
        for source, expires in ((b'a', 100), (self.source(), 0), (self.source(), True)):
            with self.assertRaises(ValueError): runner.execute_encoded(source, source_expires_ns=expires)
        self.assertEqual(self.fake.execute_calls, 0)

    def test_rejection_is_not_completed_or_usable(self):
        ctx = self.context(); runner = self.runner(ctx); self.fake.denied = True
        result = runner.execute_encoded(self.source(), source_expires_ns=100)
        self.assertFalse(result.usable)
        self.assertFalse(result.outputs)
        self.assertEqual(result.report['submitted'], 0)

    def test_hardcap_and_guard_do_not_publish_usable_result(self):
        ctx = self.context(); runner = self.runner(ctx)
        for hardcap, guard in ((True, False), (False, True)):
            self.fake.hardcap, self.fake.guard = hardcap, guard
            result = runner.execute_encoded(self.source(), source_expires_ns=100)
            self.assertFalse(result.usable)
            self.assertEqual(result.report['completed'], 1)

    def test_unknown_is_retained_and_cannot_close_or_retry(self):
        ctx = self.context(); runner = self.runner(ctx); self.fake.unknown = True
        with self.assertRaises(b.CompletionUnknown): runner.execute_encoded(self.source(), source_expires_ns=100)
        self.assertIn(id(ctx), b._RETAINED)
        with self.assertRaises(b.CompletionUnknown): ctx.close()
        with self.assertRaises(b.CompletionUnknown): runner.execute_encoded(self.source(), source_expires_ns=100)
        self.assertEqual(self.fake.execute_calls, 1)

    def test_completed_result_cannot_outlive_source_TTL(self):
        ctx = self.context(); runner = self.runner(ctx)
        expires = self.expires()
        result = runner.execute_encoded(self.source(), source_expires_ns=expires)
        self.assertTrue(result.usable)
        with patch.object(b.time, 'monotonic_ns', return_value=expires):
            self.assertFalse(result.usable)
        self.assertEqual(result.report['completed'], 1)

    def test_malformed_report_is_uncertain(self):
        ctx = self.context(); runner = self.runner(ctx); self.fake.bad_report = True
        with self.assertRaises(b.CompletionUnknown): runner.execute_encoded(self.source(), source_expires_ns=100)
        self.assertTrue(ctx.quarantined)

    def test_fork_rejected_before_any_native_call(self):
        ctx = self.context()
        with patch.object(b.os, 'getpid', return_value=ctx.pid + 1):
            with self.assertRaises(b.BridgeError): ctx.snapshot()

    def test_context_close_refuses_live_runner(self):
        ctx = self.context(); runner = self.runner(ctx)
        with self.assertRaises(b.BridgeError): ctx.close()
        self.assertTrue(ctx.handle)
        runner.close(); ctx.close()

    def test_yolo_adoption_detaches_old_close_exactly_once(self):
        ctx = self.context(); ctx.adopt_yolo()
        self.assertIsNone(self.owner.handle)
        self.owner.close()
        self.assertFalse(self.owner.destroyed)
        ctx.close()
        self.assertEqual(self.fake.destroyed, 1)

    def test_yolo_adoption_known_failure_restores_original(self):
        ctx = self.context(); self.fake.adopt_mode = 'reject'
        with self.assertRaises(b.BridgeError): ctx.adopt_yolo()
        self.assertEqual(self.owner.handle, 771)
        self.assertFalse(ctx.quarantined)

    def test_yolo_adoption_interruption_never_restores_ambiguous_handle(self):
        for mode in ('interrupt_before', 'interrupt_after'):
            with self.subTest(mode=mode):
                self.owner.handle = 771
                ctx = self.context(); self.fake.adopt_mode = mode
                with self.assertRaises(KeyboardInterrupt): ctx.adopt_yolo()
                self.assertIsNone(self.owner.handle)
                self.assertTrue(ctx.quarantined)
                self.assertIn(id(ctx), b._RETAINED)

    def test_yolo_success_and_missing_buffer_geometry(self):
        ctx = self.context(); ctx.adopt_yolo()
        result = ctx.execute_yolo(bytes(12), width=2, height=2, stride=6,
                                 source_expires_ns=self.expires(), primary_finish_ns=self.expires())
        self.assertTrue(result.usable)
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.outputs[0][:4], (1., 2., 3., 4.))
        with self.assertRaises(ValueError):
            ctx.execute_yolo(bytes(11), width=2, height=2, stride=6,
                             source_expires_ns=100, primary_finish_ns=100)
        self.assertEqual(self.fake.execute_calls, 1)

    def test_unknown_context_factory_result_is_retained(self):
        count = len(b._RETAINED)
        def interrupt(*args): raise KeyboardInterrupt()
        self.fake.aura_native_context_create.callback = interrupt
        with self.assertRaises(KeyboardInterrupt): self.context()
        self.assertEqual(len(b._RETAINED), count + 1)
        self.assertEqual(self.owner.handle, 771)

    def test_unknown_runner_factory_result_quarantines_context(self):
        ctx = self.context()
        def interrupt(*args): raise KeyboardInterrupt()
        self.fake.aura_native_runner_create.callback = interrupt
        with self.assertRaises(KeyboardInterrupt): self.runner(ctx)
        self.assertTrue(ctx.quarantined)

    def test_optional_requires_yolo_transfer_to_shared_gate(self):
        ctx = self.context()
        with self.assertRaises(b.BridgeError):
            b.NativeRunner(ctx, 'sface', self.model, sha(self.model), self.manifest, sha(self.manifest))
        self.assertFalse(self.fake.models)
        self.assertEqual(self.owner.handle, 771)

    def test_interrupted_context_close_never_retries_or_destroys_twice(self):
        ctx = self.context(); ctx.adopt_yolo()
        def interrupt(*args):
            self.fake.context_close(*args)
            raise KeyboardInterrupt()
        self.fake.aura_native_context_close.callback = interrupt
        with self.assertRaises(KeyboardInterrupt): ctx.close()
        self.assertTrue(ctx.quarantined)
        with self.assertRaises(b.CompletionUnknown): ctx.close()
        self.assertEqual(self.fake.destroyed, 1)
        self.assertIsNotNone(self.owner.ownership)

    def test_interrupted_runner_close_cannot_reuse_handle(self):
        ctx = self.context(); runner = self.runner(ctx)
        def interrupt(*args):
            self.fake.runner_close(*args)
            raise KeyboardInterrupt()
        self.fake.aura_native_runner_close.callback = interrupt
        with self.assertRaises(KeyboardInterrupt): runner.close()
        self.assertTrue(ctx.quarantined)
        with self.assertRaises(b.CompletionUnknown): runner.execute_encoded(self.source(), source_expires_ns=100)
        self.assertEqual(self.fake.execute_calls, 0)


if __name__ == '__main__':
    unittest.main()
