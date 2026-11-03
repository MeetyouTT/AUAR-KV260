"""Deterministic Python post-CDLL bookkeeping race; all native calls are fake."""
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import threading

snapshot = Path(__file__).with_name('binding-reviewed-initial.py')
spec = importlib.util.spec_from_file_location('binding_review_initial', snapshot)
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

    def aura_native_adopt_yolo(self, context, detector):
        assert context == 77 and detector == 1234
        self.adopted = True
        return 0

    def aura_native_context_close(self, context):
        assert context == 77
        assert self.adopted
        self.destroyed = True
        return 0


context = binding.NativeContext.__new__(binding.NativeContext)
context.pid = os.getpid()
context.owner = FakeOwner()
context.handle = 77
context.models, context.quarantined, context.adopted = {}, False, False
context.native = FakeNative()

lines, start_line = inspect.getsourcelines(binding.NativeContext.adopt_yolo)
pause_line = next(start_line + i for i, line in enumerate(lines) if 'if code != 0:' in line)
returned, resume = threading.Event(), threading.Event()
errors = []


def tracer(frame, event, arg):
    if (frame.f_code is binding.NativeContext.adopt_yolo.__code__ and
            event == 'line' and frame.f_lineno == pause_line):
        returned.set()
        assert resume.wait(5), 'test close did not finish'
    return tracer


def adopter():
    sys.settrace(tracer)
    try:
        context.adopt_yolo()
    except BaseException as error:
        errors.append(repr(error))
    finally:
        sys.settrace(None)


worker = threading.Thread(target=adopter)
worker.start()
assert returned.wait(5), 'adopt never reached post-native bookkeeping'
try:
    context.close()
finally:
    resume.set()
    worker.join(5)
assert not worker.is_alive() and not errors, errors
assert context.handle == 0 and context.adopted and context.native.destroyed
assert not context.owner.closed
print(json.dumps({
    'counterexample_reproduced': True,
    'closed_context_marked_adopted': context.adopted,
    'native_detector_destroyed': context.native.destroyed,
    'python_owner_fd_close_skipped': not context.owner.closed,
    'binding_sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    'scope': 'captured binding with fake native calls and explicit post-call thread interleaving',
    'real_native_calls': 0,
}))
