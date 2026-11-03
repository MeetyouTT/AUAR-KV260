"""Deterministic virtual-time checks of the pinned service, with dependency fakes.

No numpy, model runner, devices, network, real threads, or CPU load loops.
These demonstrate permitted software paths, not a board fault reproduction.
"""
import hashlib
import importlib.util
import json
import sys
import threading
import types
from pathlib import Path


SOURCE = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/'
              '2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py')
PIN = 'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0'


class SlotUnavailable(RuntimeError):
    pass


def load():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PIN
    modules = {
        'board.interaction.ui_contract': types.SimpleNamespace(millis=lambda: 0),
        'board.vision.reference_core': types.SimpleNamespace(
            FaceTracks=lambda *a, **k: types.SimpleNamespace(tracks={}), valid_box=lambda *a: None),
        'board.vision.dpu_vision_runtime': types.SimpleNamespace(SlotUnavailable=SlotUnavailable),
    }
    previous = {name: sys.modules.get(name) for name in modules}
    sys.modules.update(modules)
    spec = importlib.util.spec_from_file_location('pinned_face_targets_audit', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, previous


def main():
    module, previous = load()
    try:
        now = [100]
        service = module.FaceTargetService(lambda: None, lambda *a: None, 'synthetic', clock=lambda: now[0])
        service.ready = True
        service.stamp = 0
        service.count = 1
        service.key = {'synthetic': 1}
        service.tracks = [{'synthetic': 1}]
        service.offer(object(), 1, 0)
        old = service.pending
        service.offer(object(), 2, 80)
        assert service.pending is not old and service.pending[1:] == (2, 80)

        class Denied:
            def detect(self, image):
                raise SlotUnavailable('synthetic admission rejection')

        for index in range(4):
            now[0] = 100 + index * 240
            packet = (object(), index + 3, now[0])
            service.process(packet, Denied())
            assert service.stamp == 0 and service.processed == 0
        assert service.discarded == 4
        now[0] = 1060
        assert service.health()['ready'] is True
        assert service.health()['source_age_ms'] == 1060
        assert service.current_target() is None
        assert service.view()['face_count'] == 0 and service.view()['face_targets'] == []
        rejected_at_entry = service.discarded
        service.process((object(), 8, 0), Denied())
        assert service.discarded == rejected_at_entry + 1

        class NeverCalled:
            def detect(self, image):
                raise AssertionError('Expired source must never reach detector')

        service.process((object(), 9, 0), NeverCalled())

        # Run the real work() loop with a virtual condition/clock. A rejected
        # attempt takes 40 ms; the next latest-frame attempt starts 240 ms later.
        seconds = [0.]
        starts = []
        worker = module.FaceTargetService(lambda: None, lambda *a: None, 'synthetic',
                                          clock=lambda: round(seconds[0] * 1000))
        module.time = types.SimpleNamespace(monotonic=lambda: seconds[0])

        class Condition:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def wait_for(self, predicate):
                if not worker.closed and worker.pending is None:
                    worker.pending = (object(), len(starts) + 1, round(seconds[0] * 1000))
                assert predicate()

            def wait(self, duration):
                seconds[0] += duration
                worker.pending = (object(), len(starts) + 1, round(seconds[0] * 1000))

        class WorkerDenied:
            def detect(self, image):
                starts.append(seconds[0])
                seconds[0] += .04
                if len(starts) == 2:
                    worker.closed = True
                raise SlotUnavailable('synthetic admission rejection')

        worker.condition = Condition()
        worker.factory = WorkerDenied
        worker.lock = threading.RLock()
        worker.work()
        assert len(starts) == 2 and abs(starts[1] - starts[0] - .24) < 1e-9
        assert worker.discarded == 2 and not worker.error
        result = {
            'scope': 'Pinned source + dependency fakes + virtual time, not hardware verification',
            'checks_passed': [
                'offer retains only latest pending packet',
                'SlotUnavailable preserves previous stamp and increments discarded',
                'four illustrative repeated rejections can leave prior result over TTL',
                'ready health can be true while result is expired and hidden',
                'expired packet is rejected before detector',
                'real work loop waits 200ms after a 40ms rejected attempt',
            ],
            'worker_attempt_start_ms': [round(x * 1000, 6) for x in starts],
            'production_sources_modified': False,
        }
        path = Path(__file__).resolve().parent / 'local-path-checks.json'
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


if __name__ == '__main__':
    main()
