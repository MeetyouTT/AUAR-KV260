"""Public mock ABI, protocol, ownership and passive-observation checks."""
import ast
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

import query_display
import read_only_guard as guard
import run_query
import xcb_screensaver as subject


class Function:
    def __init__(self, function):
        self.function = function

    def __call__(self, *arguments):
        return self.function(*arguments)


class FakeLibrary:
    def __init__(self):
        self.now = 100.
        self.buffers = []
        self.requests = []
        self.freed = []
        self.disconnects = []
        self.mode = 'normal'
        self.sequence = 10
        self.extension_present = 1
        self.version = (1, 1)
        self.last_opcode = None
        callbacks = dict(xcb_connect=lambda *args: 123,
            xcb_connection_has_error=lambda *args: int(self.mode == 'lost'),
            xcb_disconnect=lambda value: self.disconnects.append(value),
            xcb_get_extension_data=self.extension, xcb_send_request=self.send,
            xcb_poll_for_reply=self.poll, xcb_flush=lambda *args: 1,
            xcb_get_file_descriptor=lambda *args: 42,
            free=lambda value: self.freed.append(value.value))
        for name, callback in callbacks.items():
            setattr(self, name, Function(callback))

    def buffer(self, raw):
        value = C.create_string_buffer(raw, len(raw))
        self.buffers.append(value)
        return C.addressof(value)

    def extension(self, connection, extension):
        raw = bytearray(32)
        raw[0], raw[8], raw[9] = 1, self.extension_present, 169
        return self.buffer(bytes(raw))

    def send(self, connection, flags, vectors, request_pointer):
        request = C.cast(request_pointer, C.POINTER(subject.ProtocolRequest)).contents
        self.requests.append(dict(flags=flags, count=request.count, opcode=request.opcode,
            isvoid=request.isvoid, extension=request.ext.contents.name,
            payload=C.string_at(vectors[0].base, vectors[0].length),
            scratch_lengths=[vectors[-2].length, vectors[-1].length], pad_length=vectors[1].length))
        self.last_opcode = request.opcode
        self.sequence += 1
        return self.sequence

    def poll(self, connection, sequence, reply, error):
        if self.mode in ('timeout', 'lost'):
            return 0
        if self.mode == 'xerror':
            error._obj.value = self.buffer(bytes(32))
            return 1
        raw = bytearray(32)
        struct.pack_into('=BBHI', raw, 0, 1, 0, sequence & 65535, 0)
        if self.last_opcode == 0:
            struct.pack_into('=HH', raw, 8, *self.version)
        else:
            struct.pack_into('=IIII', raw, 8, 0x1234, 599000, 4321, 0)
            raw[24] = 1
        if self.mode == 'wrong_sequence':
            struct.pack_into('=H', raw, 2, (sequence + 1) & 65535)
        if self.mode == 'oversized_reply':
            struct.pack_into('=I', raw, 4, 1)
        reply._obj.value = self.buffer(bytes(raw))
        return 1

    def wait(self, readers, writers, errors, seconds):
        self.now += seconds
        return [], [], []

    def create(self):
        return subject.XcbScreenSaver(0x12345678, library=self, free_library=self,
                                      clock=lambda: self.now, wait=self.wait)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.lib = FakeLibrary()

    def test_query_only_version_and_info_and_exact_root(self):
        connection = self.lib.create()
        value = connection.query()
        self.assertEqual(value, dict(xss_idle_ms=4321, xss_state=0, xss_kind=1))
        self.assertEqual([row['opcode'] for row in self.lib.requests], [0, 1])
        self.assertEqual(self.lib.requests[0]['payload'], b'\0\0\0\0\1\1\0\0')
        self.assertEqual(struct.unpack('=BBHI', self.lib.requests[1]['payload']), (0, 0, 0, 0x12345678))
        self.assertEqual(connection.version, [1, 1])
        self.assertEqual(connection.major_opcode, 169)

    def test_iovec_scratch_and_checked_reply_request_are_valid(self):
        self.lib.create()
        row = self.lib.requests[0]
        self.assertEqual((row['count'], row['isvoid'], row['flags']), (2, 0, 1))
        self.assertEqual(row['scratch_lengths'], [0, 0])
        self.assertEqual(row['pad_length'], 0)
        self.assertEqual(row['extension'], b'MIT-SCREEN-SAVER')

    def test_reply_memory_freed_and_connection_closed_once(self):
        connection = self.lib.create()
        connection.query()
        self.assertEqual(len(self.lib.freed), 2)
        connection.close()
        connection.close()
        self.assertEqual(self.lib.disconnects, [123])

    def test_missing_extension_does_not_send_or_write(self):
        self.lib.extension_present = 0
        with self.assertRaisesRegex(subject.Refused, '^SCREENSAVER_EXTENSION_UNAVAILABLE$'):
            self.lib.create()
        self.assertEqual(self.lib.requests, [])
        self.assertEqual(self.lib.disconnects, [123])

    def test_bad_version_closes_after_read_only_negotiation(self):
        self.lib.version = (2, 0)
        with self.assertRaisesRegex(subject.Refused, '^SCREENSAVER_VERSION_UNSUPPORTED$'):
            self.lib.create()
        self.assertEqual([row['opcode'] for row in self.lib.requests], [0])
        self.assertEqual(self.lib.disconnects, [123])

    def test_query_timeout_is_two_seconds(self):
        connection = self.lib.create()
        self.lib.mode = 'timeout'
        with self.assertRaisesRegex(subject.Refused, '^XCB_QUERY_TIMEOUT$'):
            connection.query()
        self.assertAlmostEqual(self.lib.now, 102.)

    def test_connection_failure_returns_without_wait(self):
        connection = self.lib.create()
        self.lib.mode = 'lost'
        with self.assertRaisesRegex(subject.Refused, '^XCB_CONNECTION_LOST$'):
            connection.query()
        self.assertEqual(self.lib.now, 100.)

    def test_x_error_memory_is_freed(self):
        connection = self.lib.create()
        self.lib.mode = 'xerror'
        with self.assertRaisesRegex(subject.Refused, '^XCB_QUERY_REJECTED$'):
            connection.query()
        self.assertEqual(len(self.lib.freed), 2)

    def test_wrong_sequence_is_rejected_and_freed(self):
        connection = self.lib.create()
        self.lib.mode = 'wrong_sequence'
        with self.assertRaises(subject.Refused):
            connection.query()
        self.assertEqual(len(self.lib.freed), 2)

    def test_variable_length_reply_is_rejected(self):
        connection = self.lib.create()
        self.lib.mode = 'oversized_reply'
        with self.assertRaises(subject.Refused):
            connection.query()

    def test_write_opcode_rejected_before_send(self):
        connection = self.lib.create()
        for opcode in (2, 3, 4, 5, 255, True):
            with self.assertRaisesRegex(subject.Refused, '^READONLY_OPCODE_REQUIRED$'):
                connection._reply(opcode)
        self.assertEqual([row['opcode'] for row in self.lib.requests], [0])

    def test_reply_sequence_wrap(self):
        self.lib.sequence = 0x10001
        connection = self.lib.create()
        self.assertEqual(connection.query()['xss_idle_ms'], 4321)

    def test_request_struct_native_abi_offsets(self):
        pointer_size = C.sizeof(C.c_void_p)
        self.assertEqual(subject.Extension.global_id.offset, pointer_size)
        self.assertEqual(subject.ProtocolRequest.ext.offset, C.sizeof(C.c_size_t))
        self.assertEqual(subject.ProtocolRequest.opcode.offset, C.sizeof(C.c_size_t) + pointer_size)
        self.assertEqual(C.sizeof(subject.IOVec), pointer_size + C.sizeof(C.c_size_t))


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.
        self.original = False
        self.tick = True

    def sleep(self, seconds):
        self.now += seconds

    def query(self):
        return dict(screen_saver=guard.ORIGINAL if self.original else guard.TEMPORARY,
            dpms_enabled=self.original, dpms_level=0, dpms_timeouts=[600, 600, 600],
            xss_idle_ms=int((self.now % 5 if self.tick else self.now) * 1000),
            xss_state=0 if self.original else 3, xss_kind=0)

    def test_temporary_policy_can_report_disabled_state(self):
        result = query_display.collect(self, lambda: {}, 'temporary', 30, lambda: self.now, self.sleep)
        self.assertEqual(len(result['samples']), 31)
        self.assertEqual(result['idle_drop_count'], 6)
        self.assertTrue(result['observed_periodic_idle_resets'])

    def test_original_policy_with_idle_drops_retains_full_semantics(self):
        self.original = True
        result = query_display.collect(self, lambda: {}, 'original', 30, lambda: self.now, self.sleep)
        self.assertTrue(result['observed_periodic_idle_resets'])
        self.assertEqual(result['max_idle_ms'], 4000)

    def test_missing_resets_remain_observed_failure_without_policy_write(self):
        self.tick = False
        result = query_display.collect(self, lambda: {}, 'temporary', 30, lambda: self.now, self.sleep)
        self.assertFalse(result['observed_periodic_idle_resets'])
        self.assertEqual(result['max_idle_ms'], 30000)

    def test_original_policy_does_not_accept_disabled_state(self):
        value = dict(self.query(), screen_saver=guard.ORIGINAL, dpms_enabled=True)
        with self.assertRaises(guard.Refused):
            query_display.validate_policy(value, 'original')

    def test_wrong_policy_never_gets_silently_corrected(self):
        with self.assertRaises(guard.Refused):
            query_display.collect(self, lambda: {}, 'original', 0, lambda: self.now, self.sleep)
        self.assertFalse(self.original)

    def test_live_owner_or_pause_change_stops_observation(self):
        def changed():
            if self.now >= 2.:
                raise guard.Refused('LIVE_PAUSE_CHANGED')
            return {}
        with self.assertRaisesRegex(guard.Refused, '^LIVE_PAUSE_CHANGED$'):
            query_display.collect(self, changed, 'temporary', 30, lambda: self.now, self.sleep)
        self.assertEqual(self.now, 2.)

    def test_exception_text_is_not_exported(self):
        self.assertNotIn('private', json.dumps(query_display.metadata(ValueError('private message'))))


class PackagingTests(unittest.TestCase):
    def test_only_readonly_symbols_and_extension_opcodes_present(self):
        source = Path(subject.__file__).read_text('utf-8')
        for token in ('XSetScreenSaver', 'XResetScreenSaver', 'DPMSDisable', 'DPMSEnable',
                      'DPMSForceLevel', 'DPMSSetTimeouts', 'XScreenSaverSuspend'):
            self.assertNotIn(token, source)

    def test_guard_functions_are_exact_original_ast(self):
        old_raw = (run_query.R1 / 'display_restore.py').read_bytes()
        self.assertEqual(hashlib.sha256(old_raw).hexdigest(), run_query.PINS['display_restore.py'])
        old = {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(old_raw).body
               if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        current = ast.parse(Path(guard.__file__).read_bytes())
        for node in current.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                self.assertEqual(ast.dump(node, include_attributes=False), old[node.name])

    def test_actual_sealed_inputs_and_85_second_remote_bound(self):
        common, arguments = run_query.local_inputs()
        self.assertEqual(arguments['baseline_owners']['gtk']['pid'], 171274)
        self.assertEqual(arguments['spec']['component_pins'], 380)
        self.assertIn('signal.alarm(85)', run_query.build_remote())

    def test_no_real_X_library_loaded_on_import(self):
        with patch.object(C, 'CDLL', side_effect=AssertionError('real library forbidden')):
            lib = FakeLibrary()
            self.assertEqual(lib.create().query()['xss_idle_ms'], 4321)


if __name__ == '__main__':
    unittest.main(verbosity=2)
