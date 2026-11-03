"""Real ARM/Ethernet Date check using staged source and a private test directory.

Only /health is requested. No model generation, production DB or system date
change occurs. This file is sent by the root only after the renderer window ends.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-root', type=Path, required=True)
    parser.add_argument('--utc-min', type=float, required=True)
    parser.add_argument('--utc-max', type=float, required=True)
    args = parser.parse_args()
    signal.alarm(25)
    root = args.candidate_root
    assert root.parent == Path('/home/root/aura-board-owner-candidate-20261030')
    assert root.name.startswith('resume-') and not root.is_symlink()
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['purpose'] == 'source_only_board_business_candidate'
    assert 0 < args.utc_max - args.utc_min <= 7 * 86400
    for name in ('common/board_timeline_clock.py', 'common/board_memory.py',
                 'board/runtime/board_dialogue_client.py'):
        assert hashlib.sha256((root / 'code' / name).read_bytes()).hexdigest() == manifest['source_sha256'][name]
    sys.path.insert(0, str(root / 'code'))
    from common.board_timeline_clock import ClockUnavailable, StableTimelineClock
    from common.board_memory import BoardMemoryStore
    from board.runtime.board_dialogue_client import InferenceHttpClient
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot == manifest['source_boot']
    client = InferenceHttpClient('192.168.50.1', 8797)
    wall_before = time.time()
    with tempfile.TemporaryDirectory(prefix='public-clock-check-', dir=str(root)) as directory:
        anchor = Path(directory) / 'clock.json'
        options = dict(utc_bounds=(args.utc_min, args.utc_max), anchor_path=anchor, monotonic=client.clock)
        clock = StableTimelineClock(boot, client.health_date_source_id(), client.validate_sample, **options)
        assert not clock.safe_for_compaction()
        began = time.monotonic()
        quality = client.sample_health_date(clock, deadline=began + 3)
        assert quality['safe_for_compaction'] and anchor.stat().st_mode & 0o077 == 0
        first = clock.event_time()
        restored = StableTimelineClock(boot, client.health_date_source_id(), client.validate_sample, **options)
        assert restored.safe_for_compaction() and abs(restored.event_time() - first) < .25
        different = StableTimelineClock('public-different-boot', client.health_date_source_id(), client.validate_sample, **options)
        try:
            different.event_time()
        except ClockUnavailable:
            pass
        else:
            raise AssertionError('An anchor from a different boot was used')
        store = BoardMemoryStore(Path(directory) / 'public-synthetic.sqlite3', clock=clock.event_time)
        scope = dict(kind='device', id='public-clock-check')
        store.append_event(scope, 'public-clock-event', 'device_event', '公开时钟接线检查。',
                           metadata=dict(time_basis='verified_health_date_monotonic', evidence='device_confirmed'))
        row = store.history(scope)[0]
        assert abs(row['recorded_utc'] - clock.event_time()) < .5
        # Expiry disables deletion but leaves already-anchored same-boot recording usable.
        short_options = dict(options, anchor_path=Path(directory) / 'short-clock.json', verified_ttl_seconds=.1)
        short = StableTimelineClock(boot, client.health_date_source_id(), client.validate_sample, **short_options)
        client.sample_health_date(short, deadline=time.monotonic() + 3)
        before_expiry = short.event_time()
        time.sleep(.15)
        assert short.event_time() >= before_expiry and not short.safe_for_compaction()
        try:
            with short.compaction_guard():
                raise AssertionError('Expired clock admitted cleanup')
        except ClockUnavailable:
            pass
        result = dict(status='PASS', actual_arm=True, actual_ethernet_health_date=True,
            boot=boot, raw_wall_year=datetime.datetime.fromtimestamp(wall_before, datetime.timezone.utc).year,
            timeline_year=datetime.datetime.fromtimestamp(first, datetime.timezone.utc).year,
            uncertainty_seconds=quality['uncertainty_seconds'], same_boot_private_anchor_reload=True,
            foreign_boot_anchor_rejected=True, expiry_blocks_cleanup_preserves_recording=True,
            store_record_uses_timeline=True, model_inference_performed=False,
            production_data_accessed=False, production_entry_changed=False, system_date_changed=False)
    signal.alarm(0)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
