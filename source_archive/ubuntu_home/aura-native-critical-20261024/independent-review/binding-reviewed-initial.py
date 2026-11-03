"""Pinned ctypes boundary for the isolated native candidate, not production.

The production scheduler/adapters still need a joint migration. No module import
loads a DSO or model. All execution uses CDLL (not PyDLL or Python callbacks).
The C++ context owns adopted YOLO and optional-runner storage until confirmed
quiescent close. Unknown calls retain the Python context as well.
"""
import ctypes as C
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time


FINGERPRINT = '0x101000056010407'
_RETAINED = {}


class BridgeError(RuntimeError):
    pass


class CompletionUnknown(BridgeError):
    native_execution_unknown = True


class Report(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in
                ('abi_version', 'outcome', 'hardcap', 'guard', 'submitted', 'completed')]
    _fields_ += [('native_status', C.c_int32), ('task', C.c_uint32)]
    _fields_ += [(n, C.c_uint64) for n in
                ('start_ns', 'native_return_ns', 'release_decision_ns', 'after_unlock_ns')]


class TensorInfo(C.Structure):
    _fields_ = [('rank', C.c_uint32), ('dims', C.c_int32 * 8),
                ('fix_point', C.c_int32), ('bytes', C.c_uint64), ('name', C.c_char * 256)]


class Buffer(C.Structure):
    _fields_ = [('data', C.c_void_p), ('bytes', C.c_uint64)]


class State(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in
                ('abi_version', 'active', 'fenced', 'primary_waiting')]
    _fields_ += [('next_primary_ns', C.c_uint64), ('disabled', C.c_uint32 * 3),
                 ('reserved', C.c_uint32), ('admissions', C.c_uint64 * 3),
                 ('overruns', C.c_uint64 * 3)]


def _pinned(path, digest):
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('Explicit lowercase SHA256 required')
    path = Path(path).resolve(strict=True)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Pinned artifact differs: ' + path.name)
    return path


def _ns(value):
    if type(value) is not int or not 0 < value < 2 ** 63:
        raise ValueError('Positive CLOCK_MONOTONIC nanoseconds required')
    return value


def _report(value, task):
    result = {name: getattr(value, name) for name, _ in Report._fields_}
    if (result['abi_version'] != 1 or result['task'] != task or
            not 0 <= result['outcome'] <= 8 or
            any(result[n] not in (0, 1) for n in ('hardcap', 'guard', 'submitted', 'completed'))):
        raise CompletionUnknown('Invalid native report; context retained')
    if result['completed'] and not result['submitted']:
        raise CompletionUnknown('Inconsistent completion report')
    if result['start_ns'] and not (result['start_ns'] <= result['native_return_ns'] <=
            result['release_decision_ns'] <= result['after_unlock_ns']):
        raise CompletionUnknown('Invalid native time ordering')
    return result


@dataclass(frozen=True)
class Execution:
    report: dict
    outputs: tuple
    returned_mono_ns: int

    @property
    def usable(self):
        # Business TTL/probation checks remain mandatory in the integration.
        r = self.report
        return (r['outcome'] == 0 and r['submitted'] == r['completed'] == 1 and
                r['native_status'] == 0 and not r['hardcap'] and not r['guard'])


class NativeContext:
    def __init__(self, owner, library, library_sha256):
        self.pid = os.getpid()
        self.owner, self.handle = owner, 0
        self.models, self.quarantined = {}, False
        self.adopted = False
        if owner.fingerprint != FINGERPRINT or owner.ownership is None or not owner.handle:
            raise ValueError('The existing live pinned DPU owner is required')
        bridge = _pinned(library, library_sha256)
        yolo = _pinned(owner.config['native_library'], owner.config['native_sha256'])
        # CDLL releases the GIL for the entire C entry. PyDLL is prohibited.
        self.native = C.CDLL(str(bridge))
        self._configure()
        if (self.native.aura_native_abi() != 1 or
                self.native.aura_native_report_size() != C.sizeof(Report) or
                self.native.aura_native_state_size() != C.sizeof(State)):
            raise BridgeError('Native ABI or structure size differs')
        self.handle = self.native.aura_native_context_create(owner.ownership.fileno(), str(yolo).encode())
        if not self.handle:
            raise BridgeError(self._error())

    def _configure(self):
        signatures = {
            'abi': (C.c_uint32, []), 'report_size': (C.c_uint32, []),
            'state_size': (C.c_uint32, []), 'error': (C.c_char_p, []),
            'context_create': (C.c_uint64, [C.c_int, C.c_char_p]),
            'context_close': (C.c_int, [C.c_uint64]),
            'adopt_yolo': (C.c_int, [C.c_uint64, C.c_void_p]),
            'snapshot': (C.c_int, [C.c_uint64, C.POINTER(State)]),
            'announce_primary': (C.c_int, [C.c_uint64, C.c_uint64]),
            'runner_create': (C.c_uint64, [C.c_uint64, C.c_uint, C.c_char_p]),
            'runner_close': (C.c_int, [C.c_uint64, C.c_uint64]),
            'tensor_info': (C.c_int, [C.c_uint64, C.c_uint64, C.c_uint, C.c_uint, C.POINTER(TensorInfo)]),
            'optional_execute': (C.c_int, [C.c_uint64, C.c_uint64, C.c_void_p, C.c_uint64,
                C.POINTER(Buffer), C.c_uint, C.c_uint64, C.POINTER(Report)]),
            'yolo_execute': (C.c_int, [C.c_uint64, C.c_void_p, C.c_int, C.c_int, C.c_int,
                C.POINTER(C.c_float), C.c_int, C.c_int, C.POINTER(C.c_int),
                C.c_uint64, C.c_uint64, C.POINTER(Report)]),
        }
        for name, (result, args) in signatures.items():
            function = getattr(self.native, 'aura_native_' + name)
            function.restype, function.argtypes = result, args

    def _error(self):
        return (self.native.aura_native_error() or b'Native candidate error').decode(errors='replace')

    def _check(self):
        # Never touch an inherited C++ mutex or library registry after fork.
        if os.getpid() != self.pid:
            raise BridgeError('Fork-inherited native binding rejected')
        if not self.handle:
            raise BridgeError('Native context is closed')
        if self.quarantined:
            raise CompletionUnknown('Native context retained after uncertain call')

    def _retain(self, *values):
        self.quarantined = True
        _RETAINED[id(self)] = (self, values)

    def adopt_yolo(self):
        self._check()
        # Detach BEFORE the GIL-releasing call. Even asynchronous Python
        # exceptions must not leave the original close path owning this handle.
        with self.owner.lock:
            pointer = self.owner.handle
            if not pointer or self.adopted:
                raise BridgeError('YOLO must be adopted exactly once')
            rejected = False
            try:
                self.owner.handle = None
                code = self.native.aura_native_adopt_yolo(self.handle, pointer)
                if code != 0:
                    # Native adopt has the strong exception guarantee: a
                    # negative return has not transferred detector ownership.
                    self.owner.handle = pointer
                    rejected = True
                    raise BridgeError(self._error())
                self.adopted = True
            except BaseException:
                if not rejected:
                    self._retain(pointer)
                raise

    def snapshot(self):
        self._check()
        state = State()
        if self.native.aura_native_snapshot(self.handle, C.byref(state)) != 0:
            raise BridgeError(self._error())
        if state.abi_version != 1:
            raise BridgeError('Native state ABI differs')
        return {name: list(value) if isinstance(value, C.Array) else value
                for name, _ in State._fields_ for value in (getattr(state, name),)}

    def announce_primary(self, deadline_ns):
        self._check()
        if self.native.aura_native_announce_primary(self.handle, _ns(deadline_ns)) != 0:
            raise BridgeError(self._error())

    def execute_yolo(self, bgr, *, width, height, stride, source_expires_ns, primary_finish_ns):
        self._check()
        if not self.adopted:
            raise BridgeError('YOLO ownership has not been transferred')
        if (any(type(v) is not int for v in (width, height, stride)) or
                not 0 < width <= 4096 or not 0 < height <= 4096 or stride < width * 3):
            raise ValueError('Bounded uint8 BGR geometry required')
        _ns(source_expires_ns)
        _ns(primary_finish_ns)
        view = memoryview(bgr)
        if (not view.c_contiguous or view.itemsize != 1 or view.format not in ('B', 'b', 'c') or
                not (height - 1) * stride + width * 3 <= view.nbytes <= 64 * 1024 ** 2):
            raise ValueError('BGR buffer does not cover the declared geometry')
        source = (C.c_ubyte * view.nbytes).from_buffer_copy(view)
        output, count, report = (C.c_float * (16 * 6))(), C.c_int(), Report()
        try:
            code = self.native.aura_native_yolo_execute(self.handle, source, width, height, stride,
                output, 16, 0, C.byref(count), source_expires_ns, primary_finish_ns, C.byref(report))
            returned = time.monotonic_ns()
            if code == -1 and not report.abi_version:
                raise BridgeError(self._error())
            result = _report(report, 0)
            if code == -2 or result['outcome'] == 5:
                raise CompletionUnknown(self._error())
            if code not in (0, 1):
                raise BridgeError(self._error())
            if code == 0 and not (result['outcome'] == 0 and result['submitted'] == result['completed'] == 1
                                 and result['native_status'] == 0):
                raise CompletionUnknown('YOLO success did not confirm native completion')
            if not 0 <= count.value <= 16:
                raise BridgeError('YOLO output count outside original capacity')
            rows = tuple(tuple(output[i * 6:i * 6 + 6]) for i in range(count.value)) if code == 0 else ()
            return Execution(result, rows, returned)
        except BridgeError as exc:
            if isinstance(exc, CompletionUnknown):
                self._retain(source, output, count)
            raise
        except BaseException:
            self._retain(source, output, count)
            raise

    def close(self):
        self._check()
        # Native close refuses referenced runners, active jobs and fence. This
        # method never clears a fence, destroys/recreates a context or retries.
        if self.native.aura_native_context_close(self.handle) != 0:
            raise BridgeError(self._error())
        self.handle = 0
        # owner.handle is detached after adoption; parent closes only its FD.
        if self.adopted:
            self.owner.close()


class NativeRunner:
    def __init__(self, context, task, model_path, model_sha256, manifest_path, manifest_sha256):
        context._check()
        if task not in ('yunet', 'sface'):
            raise ValueError('Only pinned optional models are supported')
        self.context, self.task = context, 1 if task == 'yunet' else 2
        self.handle = 0
        model = _pinned(model_path, model_sha256)
        manifest = json.loads(_pinned(manifest_path, manifest_sha256).read_text())
        partitions = [p for p in manifest['partitions'] if p['device'] == 'DPU']
        if (manifest['sha256'] != model_sha256 or len(partitions) != 1 or
                partitions[0]['fingerprint'] != FINGERPRINT):
            raise ValueError('Pinned xmodel manifest differs')
        expected = partitions[0]
        if len(expected['inputs']) != 1 or len(expected['outputs']) != (4 if task == 'yunet' else 1):
            raise ValueError('Unexpected manifest port count')
        self.handle = context.native.aura_native_runner_create(context.handle, self.task, str(model).encode())
        if not self.handle:
            raise BridgeError(context._error())
        # Keep strong ownership before any subsequent validation can fail.
        context.models[self.handle] = self
        try:
            self.inputs = self._metadata(False, len(expected['inputs']))
            self.outputs = self._metadata(True, len(expected['outputs']))
            for actual, target in ((self.inputs, expected['inputs']), (self.outputs, expected['outputs'])):
                if (len({t['name'] for t in actual}) != len(actual) or
                        {t['name']: t for t in actual} != {t['name']: t for t in target}):
                    raise ValueError('Native VART tensor ports differ from the pinned manifest')
            expected_shape = [1, 320, 320, 3] if task == 'yunet' else [1, 112, 112, 3]
            if self.inputs[0]['dims'] != expected_shape or self.inputs[0]['fix_point'] != 7:
                raise ValueError('Unexpected pinned input quantization or shape')
            if task == 'sface' and (self.outputs[0]['dims'] != [1, 128] or self.outputs[0]['fix_point'] != 5):
                raise ValueError('Unexpected SFace INT8 feature contract')
        except BaseException:
            self.close()
            raise

    def _metadata(self, output, count):
        result = []
        for i in range(count):
            info = TensorInfo()
            if self.context.native.aura_native_tensor_info(self.context.handle, self.handle,
                    int(output), i, C.byref(info)) != 0:
                raise BridgeError(self.context._error())
            if not 1 <= info.rank <= 8:
                raise ValueError('Native tensor rank outside contract')
            dims = list(info.dims)[:info.rank]
            size = 1
            for dimension in dims:
                if dimension <= 0:
                    raise ValueError('Native tensor has an invalid dimension')
                size *= dimension
            if size != info.bytes or not 0 < size <= 64 * 1024 ** 2:
                raise ValueError('Native tensor byte size outside contract')
            result.append({'name': info.name.decode('utf-8', errors='strict'), 'dims': dims,
                           'dtype': 'xint8', 'fix_point': info.fix_point})
        return result

    @staticmethod
    def _bytes(meta):
        size = 1
        for d in meta['dims']:
            size *= d
        return size

    def execute_encoded(self, source, *, source_expires_ns):
        self.context._check()
        if not self.handle:
            raise BridgeError('Native optional runner is closed')
        _ns(source_expires_ns)
        view = memoryview(source)
        if not view.c_contiguous or view.itemsize != 1 or view.format not in ('b', 'B', 'c'):
            raise ValueError('Contiguous encoded INT8 bytes required')
        size = self._bytes(self.inputs[0])
        if view.nbytes != size:
            raise ValueError('Encoded input size differs from the pinned model')
        source_array = (C.c_int8 * size).from_buffer_copy(view)
        arrays = [(C.c_int8 * self._bytes(meta))() for meta in self.outputs]
        ports = (Buffer * len(arrays))(*(Buffer(C.cast(a, C.c_void_p), C.sizeof(a)) for a in arrays))
        report = Report()
        try:
            code = self.context.native.aura_native_optional_execute(self.context.handle, self.handle,
                source_array, size, ports, len(arrays), source_expires_ns, C.byref(report))
            returned = time.monotonic_ns()
            if code == -1 and not report.abi_version:
                raise BridgeError(self.context._error())
            result = _report(report, self.task)
            if code == -2 or result['outcome'] == 5:
                raise CompletionUnknown(self.context._error())
            if code not in (0, 1):
                raise BridgeError(self.context._error())
            if code == 0 and not (result['outcome'] == 0 and result['submitted'] == result['completed'] == 1
                                 and result['native_status'] == 0):
                raise CompletionUnknown('Success return did not confirm native completion')
            return Execution(result, tuple(bytes(a) for a in arrays) if code == 0 else (), returned)
        except BridgeError as exc:
            if isinstance(exc, CompletionUnknown):
                self.context._retain(self, source_array, arrays, ports)
            raise
        except BaseException:
            self.context._retain(self, source_array, arrays, ports)
            raise

    def close(self):
        self.context._check()
        if not self.handle:
            return
        if self.context.native.aura_native_runner_close(self.context.handle, self.handle) != 0:
            raise BridgeError(self.context._error())
        del self.context.models[self.handle]
        self.handle = 0
