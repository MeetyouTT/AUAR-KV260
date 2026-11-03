"""Exercise frozen production-equivalent Python with simulated registers/queues.

No device, network, service, database, model, or actuator access. These are
counterexamples about software contracts, not claims about physical events.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SHADOW = Path('/home/ghmd/aura-pan-follow-shadow-20261024')
CONTROL = SHADOW / 'continuous_v10r14_candidate'
QUEUE = Path('/home/ghmd/Win共享文件/协作任务/2026-10-26_音频USB告警与队列保护/audio_queue_bound_candidate')
sys.path[:0] = [str(CONTROL), str(SHADOW / 'offline_host_driver')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    from deadline_driver import DeadlineDriver
    from batch_driver import BatchDriver
    from vsrv_driver import ID, ABI, BUILD_ID
    fixtures = load('audit_deadline_fixtures', CONTROL / 'test_deadline_driver.py')
    driver, io, clock = fixtures.DeadlineTests().device(DeadlineDriver, .300)
    result = driver.submit(1470, 10., minimum_lease_ms=23)
    commit_at, lease_until = io.commits[0]
    assert result['outcome'] == 'REJECTED'
    assert commit_at > 10.250 and driver.status()['flags'] == 0

    class ExpiringRegisters:
        def __init__(self):
            self.values = {0: ID, 4: ABI, 8: BUILD_ID, 0x28: 7,
                           0x0c: 15, 0x2c: 1450, 0x30: 1,
                           0x34: 1, 0x38: 1, 0x40: 1450, 0x44: 1451}
            self.injected = False
        def read_many(self, offsets):
            values = []
            for offset in offsets:
                if offset == 0x2c and not self.injected:
                    self.values.update({0x0c: 64, 0x30: 0})
                    self.injected = True
                values.append(self.values[offset])
            return values

    snapshots = ExpiringRegisters()
    observer = BatchDriver.__new__(BatchDriver)
    observer.io, observer.build_id = snapshots, BUILD_ID
    returned = observer.status()
    assert returned['active'] and returned['lease_left_ms'] == 0
    assert snapshots.values[0x0c] == 64

    audio_fixtures = load('audit_appsrc_fixtures', QUEUE / 'test_appsrc_queue_bound.py')
    rig = audio_fixtures.Rig(audio_fixtures.new)
    try:
        rig.source.drain = False
        rig.engine.command({'type': 'stream', 'token': 1})
        rig.engine._append(b'\x23\x01' * 24000, 'answer')
        rig.advance(.080, sink_moves=False)
        pending_content = sum(len(buf.pcm) for buf in rig.source.pushes if any(buf.pcm))
        native_before = rig.source.level
        rig.engine.command({'type': 'stop', 'token': 2})
        native_after = rig.source.level
        assert pending_content > 0 and native_after == native_before
        assert not rig.engine.active and not rig.engine.queue
        audio = dict(native_pcm_bytes_before_stop=native_before,
                     native_pcm_bytes_after_stop=native_after,
                     nonzero_content_bytes_queued=pending_content,
                     input_pcm_duration_ms=pending_content / 48000 * 1000,
                     python_queue_empty=True, pipeline_still_open=rig.engine.pipeline is not None,
                     scope='controlled stalled downstream; not an acoustic stop-latency measurement')
    finally:
        rig.engine.release()

    source_paths = [CONTROL / 'deadline_driver.py', CONTROL / 'batch_driver.py',
                    CONTROL / 'test_deadline_driver.py', QUEUE / 'gstreamer_persistent_engine.py']
    output = dict(
        scope='local Python + fake registers/queues; no hardware/network/model/database access',
        late_commit=dict(source_mono_s=10., source_deadline_mono_s=10.250,
                         injected_pause_s=.300, actual_fake_commit_mono_s=commit_at,
                         relative_lease_until_s=lease_until,
                         returned_outcome=result['outcome'], returned_reason=result['reason'],
                         stop_verified=driver.status()['flags'] == 0,
                         hardware_absolute_deadline_proven=False),
        readback_coherence=dict(returned_flags=returned['flags'],
                                returned_active=returned['active'],
                                returned_lease_ms=returned['lease_left_ms'],
                                actual_final_flags=snapshots.values[0x0c],
                                acknowledgement_unchanged=returned['ack_seq'] == 7,
                                scope='a documented best-effort multiword read, not an atomic RTL snapshot'),
        playback_stop=audio,
        source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
        probe_count=3, all_expected_counterexamples_reproduced=True)
    (ROOT / 'software_probes.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
