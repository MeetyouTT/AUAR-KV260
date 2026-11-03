"""Lifecycle serialization at the exact post-native-return bookkeeping point."""
import ast
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import threading

snapshot = Path(__file__).with_name('binding-reviewed-final.py')
spec = importlib.util.spec_from_file_location('binding_review_final', snapshot)
binding = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = binding
spec.loader.exec_module(binding)


class FakeOwner:
    def __init__(self):
        self.lock = threading.Lock()
        self.handle = 1234
        self.closed = False

    def close(self):
        self.closed = True


class FakeNative:
    def __init__(self):
        self.adopted = False
        self.destroyed = False
        self.close_entered = threading.Event()

    def aura_native_adopt_yolo(self, context, detector):
        assert context == 77 and detector == 1234
        self.adopted = True
        return 0

    def aura_native_context_close(self, context):
        self.close_entered.set()
        assert context == 77 and self.adopted
        self.destroyed = True
        return 0


context = binding.NativeContext.__new__(binding.NativeContext)
context.pid = os.getpid()
context.owner = FakeOwner()
context.handle = 77
context.models, context.quarantined, context.adopted = {}, False, False
context.native = FakeNative()
context._lifecycle = threading.RLock()

lines, start_line = inspect.getsourcelines(binding.NativeContext._adopt_yolo)
pause_line = next(start_line + i for i, line in enumerate(lines) if 'if code != 0:' in line)
returned, resume, close_attempted = threading.Event(), threading.Event(), threading.Event()
errors = []


def tracer(frame, event, arg):
    if (frame.f_code is binding.NativeContext._adopt_yolo.__code__ and
            event == 'line' and frame.f_lineno == pause_line):
        returned.set()
        assert resume.wait(5), 'test did not release post-call bookkeeping'
    return tracer


def adopter():
    sys.settrace(tracer)
    try:
        context.adopt_yolo()
    except BaseException as error:
        errors.append(repr(error))
    finally:
        sys.settrace(None)


def closer():
    close_attempted.set()
    try:
        context.close()
    except BaseException as error:
        errors.append(repr(error))


adopting = threading.Thread(target=adopter)
adopting.start()
assert returned.wait(5), 'adopt did not reach post-call point'
closing = threading.Thread(target=closer)
closing.start()
try:
    assert close_attempted.wait(5)
    acquired = context._lifecycle.acquire(blocking=False)
    if acquired:
        context._lifecycle.release()
    assert not acquired, 'lifecycle is no longer held over post-call bookkeeping'
    assert not context.native.close_entered.is_set(), 'close entered before adopt bookkeeping finished'
finally:
    resume.set()
    adopting.join(5)
    closing.join(5)
assert not adopting.is_alive() and not closing.is_alive() and not errors, errors
assert context.handle == 0 and context.adopted and context.native.destroyed
assert context.owner.closed, 'adopt/close skipped the original owner FD close'

tree = ast.parse(snapshot.read_bytes())
for class_name, method_name in [('NativeContext', 'execute_yolo'), ('NativeRunner', 'execute_encoded')]:
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)
    assert not any(isinstance(n, (ast.With, ast.AsyncWith)) for n in ast.walk(method)), \
        'execution acquired a Python context manager; review possible lease regression'

print(json.dumps({
    'passed': True,
    'post_native_adopt_bookkeeping_serialized': True,
    'owner_fd_close_preserved': True,
    'execution_methods_do_not_acquire_lifecycle_lock': True,
    'binding_sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    'scope': 'captured binding with fake native calls and explicit post-call thread interleaving',
    'real_native_calls': 0,
}))
