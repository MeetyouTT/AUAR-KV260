"""Actual CDLL/structures/candidate C++ round trip with fake VART only."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import unittest

import native_binding as b
from test_native_binding import Owner


class RealABITests(unittest.TestCase):
    def setUp(self):
        self.library = Path(os.environ['AURA_HOST_FAKE_DSO']).resolve()
        self.owner = Owner(self.library)
        self.addCleanup(self.owner.close)
        self.context = b.NativeContext(self.owner, self.library, self.sha(self.library))
        self.library_abi = self.context.native
        self.assertEqual(self.library_abi.aura_fixture_fake_only(), 1)
        self.model = self.library.parent / 'fake-model.tag'
        self.manifest = self.library.parent / 'fake-manifest.json'

    @staticmethod
    def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

    def runner(self):
        if not self.context.adopted:
            self.context.adopt_yolo()
        return b.NativeRunner(self.context, 'sface', self.model, self.sha(self.model),
                              self.manifest, self.sha(self.manifest))

    def test_optional_exact_encoded_bytes_through_real_C_ABI(self):
        runner = self.runner()
        self.context.announce_primary(time.monotonic_ns() + 1_000_000_000)
        for first in (0, 42, 127, 128, 255):
            source = bytes([first]) * (112 * 112 * 3)
            result = runner.execute_encoded(source, source_expires_ns=time.monotonic_ns() + 1_000_000_000)
            self.assertEqual(result.outputs, (bytes([first]) * 128,))
            self.assertEqual(result.report['completed'], 1)
            self.assertGreaterEqual(result.returned_mono_ns, result.report['after_unlock_ns'])
        state = self.context.snapshot()
        self.assertEqual(state['admissions'][2], 5)
        runner.close(); self.context.close()

    def test_expired_native_source_submits_nothing(self):
        runner = self.runner()
        self.context.announce_primary(time.monotonic_ns() + 1_000_000_000)
        result = runner.execute_encoded(bytes(112 * 112 * 3), source_expires_ns=1)
        self.assertEqual(result.report['submitted'], 0)
        self.assertFalse(result.usable)
        self.assertFalse(result.outputs)
        self.assertEqual(self.context.snapshot()['admissions'][2], 0)
        runner.close(); self.context.close()

    def test_unknown_native_callback_fences_and_retains_actual_context(self):
        runner = self.runner()
        self.context.announce_primary(time.monotonic_ns() + 1_000_000_000)
        self.library_abi.aura_fixture_fail_next()
        with self.assertRaises(b.CompletionUnknown):
            runner.execute_encoded(bytes(112 * 112 * 3), source_expires_ns=time.monotonic_ns() + 1_000_000_000)
        self.assertTrue(self.context.quarantined)
        self.assertIn(id(self.context), b._RETAINED)
        with self.assertRaises(b.CompletionUnknown): runner.close()
        with self.assertRaises(b.CompletionUnknown): self.context.close()

    def test_adopted_yolo_outputs_and_single_destroy_through_real_C_ABI(self):
        before = self.library_abi.aura_fixture_destroyed()
        self.context.adopt_yolo()
        self.assertIsNone(self.owner.handle)
        result = self.context.execute_yolo(bytes(12), width=2, height=2, stride=6,
            source_expires_ns=time.monotonic_ns() + 1_000_000_000,
            primary_finish_ns=time.monotonic_ns() + 100_000_000)
        self.assertEqual(result.outputs[0][:4], (1.,2.,3.,4.))
        self.context.close()
        self.assertEqual(self.library_abi.aura_fixture_destroyed(), before + 1)
        self.assertFalse(self.owner.destroyed)

    def test_CDLL_releases_GIL_for_compiled_call(self):
        # Counter increments only WHILE the compiled call is inside its sleep.
        # This avoids mistaking Python progress before/after entry for GIL release.
        stop = threading.Event()
        def other():
            while not stop.is_set(): self.library_abi.aura_fixture_try_progress()
        thread = threading.Thread(target=other);thread.start()
        try:
            self.library_abi.aura_fixture_block()
            # Exclude a single C call already in flight when the sleep begins.
            self.assertGreaterEqual(self.library_abi.aura_fixture_progress(), 10)
        finally:
            stop.set();thread.join(timeout=1)
        self.context.close()


if __name__ == '__main__': unittest.main()
