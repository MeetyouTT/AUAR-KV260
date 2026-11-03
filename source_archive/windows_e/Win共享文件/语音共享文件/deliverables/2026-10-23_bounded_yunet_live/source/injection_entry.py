"""One bounded delay after a completed real job; used only by the injected unit."""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'aura'))
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from runtime_entry import launch

original = DpuVisionSchedule.optional
injected = False


@contextmanager
def one_delay(self, kind):
    global injected
    with original(self, kind) as acquired:
        yield acquired
        if (not injected and acquired and kind == 'yunet' and self.yunet_recovery is not None
                and self.yunet_recovery.phase == 'RUNNING' and self.jobs[kind]['calls'] >= 3
                and self._native_completed and self.next_primary-self.clock() >= .060):
            injected = True
            started = time.monotonic()
            # The native job and its buffers are complete. Ample admitted
            # primary slack is required before this single wall-delay injection.
            time.sleep(.031)
            with (ROOT/'injected-once.json').open('x') as stream:
                json.dump({'one_time': True, 'requested_delay_ms': 31,
                           'started_monotonic_s': started,
                           'ended_monotonic_s': time.monotonic(),
                           'native_completed_before_delay': True}, stream)


if __name__ == '__main__':
    assert not (ROOT/'injected-once.json').exists(), 'Injected unit may not replay its one-time delay'
    DpuVisionSchedule.optional = one_delay
    launch(sys.argv[1:], root=ROOT)
