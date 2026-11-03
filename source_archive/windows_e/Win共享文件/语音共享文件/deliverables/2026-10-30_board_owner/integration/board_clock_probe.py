"""ARM/board-Ethernet UTC wiring probe; public fixtures, no model inference.

Pins below are filled from the next reviewed source-only manifest and the
temporary model endpoint immediately before use. No production database,
system date, service entry, microphone, audio device or firmware is touched.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
import urllib.request

BASE = ''
PIN = ''
ROOT = Path('/home/root/aura-board-owner-candidate-20261030/UNCONFIGURED')
MODEL_PORT = 0
UTC_WINDOW = (0, 1)


def main():
    signal.alarm(45)
    assert BASE.startswith('http://192.168.50.1:') and len(PIN) == 64
    assert 1 <= MODEL_PORT <= 65535 and UTC_WINDOW[1] - UTC_WINDOW[0] <= 7 * 86400
    parent = Path('/home/root/aura-board-owner-candidate-20261030')
    assert ROOT.parent == parent and ROOT.name.startswith('semantic-')
    assert not ROOT.is_symlink() and shutil.disk_usage('/home/root').free > 8 * 1024 * 1024
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE + '/manifest.json', timeout=3) as response:
        raw = response.read(65537)
    assert len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == PIN
    manifest = json.loads(raw)
    assert manifest['candidate_root'] == str(ROOT) and manifest['purpose'] == 'synthetic_arm_semantic_memory'
    ROOT.mkdir(parents=True, exist_ok=True)
    for entry in manifest['entries']:
        relative = Path(entry['name'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = ROOT / relative
        assert ROOT.resolve() in target.resolve().parents and not target.is_symlink()
        with opener.open(BASE + '/assets/' + entry['sha256'], timeout=3) as response:
            data = response.read(entry['bytes'] + 1)
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == data
        else:
            with target.open('xb') as stream:
                stream.write(data)
    for package in ('common', 'board', 'board/runtime'):
        init = ROOT / 'code' / package / '__init__.py'
        if not init.exists():
            init.write_bytes(b'')
    sys.path.insert(0, str(ROOT / 'code'))
    from common.board_memory import BoardMemoryStore, BoardMemoryWorker
    from common.board_timeline_clock import ClockUnavailable, StableTimelineClock
    from board.runtime.board_dialogue_client import InferenceHttpClient

    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    client = InferenceHttpClient('192.168.50.1', MODEL_PORT)
    source = client.health_date_source_id()
    board_wall = time.time()
    with tempfile.TemporaryDirectory(prefix='synthetic-clock-', dir=str(ROOT)) as temporary:
        anchor = Path(temporary) / 'private-clock.json'
        timeline = StableTimelineClock(boot, source, client.validate_sample,
            utc_bounds=UTC_WINDOW, anchor_path=anchor, monotonic=client.clock)
        assert not timeline.safe_for_compaction()
        verified = client.sample_health_date(timeline, deadline=client.clock() + 3.)
        assert verified['safe_for_compaction'] and client._date_proof is None
        assert UTC_WINDOW[0] <= timeline.event_time() <= UTC_WINDOW[1]
        assert anchor.stat().st_mode & 0o077 == 0
        restored = StableTimelineClock(boot, source, client.validate_sample,
            utc_bounds=UTC_WINDOW, anchor_path=anchor, monotonic=client.clock)
        assert restored.safe_for_compaction() and abs(restored.event_time() - timeline.event_time()) < .25
        new_boot = StableTimelineClock('synthetic-different-boot', source, client.validate_sample,
            utc_bounds=UTC_WINDOW, anchor_path=anchor, monotonic=client.clock)
        assert not new_boot.safe_for_compaction()
        try:
            new_boot.event_time()
        except ClockUnavailable:
            pass
        else:
            raise AssertionError('An anchor from another boot was adopted')

        store = BoardMemoryStore(Path(temporary) / 'synthetic.sqlite3', clock=timeline.event_time)
        scope = dict(kind='device', id='synthetic-clock-device')
        store.append_event(scope, 'public-clock-event', 'device_event', '公开时钟接线验证。',
            metadata=dict(time_basis='verified_model_health_monotonic_anchor', evidence='device_confirmed'))
        event = store.history(scope)[0]
        assert abs(event['recorded_utc'] - timeline.event_time()) < 1
        def no_model(*_):
            raise AssertionError('Clock probe must not perform inference')
        worker = BoardMemoryWorker(store, no_model, idle=lambda: timeline.safe_for_compaction(),
            compaction_guard_factory=timeline.compaction_guard)
        assert worker.step() is False and store.health()['active_bodies'] == 1
        print(json.dumps(dict(
            status='PASS', actual_arm=True, actual_ethernet_health_date=True,
            board_wall_year=datetime.fromtimestamp(board_wall, timezone.utc).year,
            anchored_utc_year=datetime.fromtimestamp(timeline.event_time(), timezone.utc).year,
            anchor_uncertainty_seconds=verified['uncertainty_seconds'],
            same_boot_restart_preserved=True, other_boot_anchor_rejected=True,
            board_store_uses_verified_clock=True, recent_body_kept=True,
            system_clock_changed=False, production_changed=False, real_database_changed=False,
            model_inference_performed=False, tts_requested=False, actual_playback=False)))


if __name__ == '__main__':
    main()
