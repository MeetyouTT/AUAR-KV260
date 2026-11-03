"""Pure local contract counterexample: Python references do not block close.

The class AST is compiled from the reference source, __init__ is bypassed,
and fake resources receive calls. No CDLL, factory, owner file or device used.
"""
import ast
import hashlib
import json
from pathlib import Path
import threading

source = Path('/home/ghmd/Win共享文件/语音共享文件/aura/board/vision/yolo_dpu.py')
raw = source.read_bytes()
tree = ast.parse(raw, filename=str(source))
node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'DpuYoloX')
namespace = {}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)


class FakeNative:
    destroyed = []

    def aura_yolox_destroy(self, handle):
        self.destroyed.append(handle)


class FakeOwner:
    closed = False

    def close(self):
        self.closed = True


detector = namespace['DpuYoloX'].__new__(namespace['DpuYoloX'])
detector.lock = threading.Lock()
detector.native = FakeNative()
detector.handle = 123
detector.ownership = FakeOwner()
owner = detector.ownership
quarantine_strong_reference = [detector]
detector.close()
assert detector.native.destroyed == [123]
assert owner.closed and detector.handle is None and detector.ownership is None
assert quarantine_strong_reference[0] is detector
print(json.dumps({
    'explicit_close_bypasses_strong_reference_retention': True,
    'reference_yolo_source_sha256': hashlib.sha256(raw).hexdigest(),
    'factory_calls': 0,
    'real_native_calls': 0,
    'scope': 'reference class close method with fake resources; not a board test',
}))
