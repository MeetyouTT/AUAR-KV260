"""Natural five-minute retention on ARM, with only an explicit public fixture.

Uses the verified Windows Date/board monotonic clock and the real fixed 27B.
It never changes time or touches an existing business store. All fixture data
and its temporary board-mode database are removed at normal completion.
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
    parser.add_argument('--candidate-root', required=True, type=Path)
    parser.add_argument('--utc-min', required=True, type=float)
    parser.add_argument('--utc-max', required=True, type=float)
    args = parser.parse_args()
    root = args.candidate_root
    assert root.parent == Path('/home/root/aura-board-owner-candidate-20261030')
    assert root.name.startswith('resume-') and not root.is_symlink()
    manifest = json.loads((root/'manifest.json').read_text())
    assert manifest['purpose'] == 'source_only_board_business_candidate'
    for name in ('common/board_memory.py', 'common/board_timeline_clock.py',
                 'board/runtime/board_memory_policy.py', 'board/runtime/board_dialogue_client.py'):
        assert hashlib.sha256((root/'code'/name).read_bytes()).hexdigest() == manifest['source_sha256'][name]
    signal.alarm(390)
    sys.path.insert(0, str(root/'code'))
    from common.board_memory import BoardMemoryStore, BoardMemoryWorker
    from common.board_timeline_clock import StableTimelineClock
    from board.runtime.board_dialogue_client import InferenceHttpClient
    from board.runtime.board_memory_policy import BoardContextBuilder, BoardSummaryClient
    from tools.dialogue_host_ollama import fast_system_prompt
    from common.device_policy import MODEL_HINT
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot == manifest['source_boot']
    http = InferenceHttpClient('192.168.50.1', 8797)
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='public-natural-retention-', dir=str(root)) as directory:
        timeline = StableTimelineClock(boot, http.health_date_source_id(), http.validate_sample,
            utc_bounds=(args.utc_min, args.utc_max), anchor_path=Path(directory)/'clock.json')
        http.sample_health_date(timeline, deadline=time.monotonic()+3)
        store = BoardMemoryStore(Path(directory)/'public-board-mode.sqlite3',
                                 clock=timeline.event_time, data_origin='board')
        scope = dict(kind='device', id='public-retention-fixture')
        store.append_event(scope, 'public-plan', 'user_said', '公开测试：小林计划周五买3本书，尚未购买。',
            metadata=dict(names=['小林'], numbers=[3], negated=True, status='planned', evidence='statement'))
        recorded = time.monotonic()
        class CountedClient:
            calls = 0
            first_call_seconds = None
            def request(self, kind, payload, **kwargs):
                self.calls += 1
                if self.first_call_seconds is None:
                    self.first_call_seconds = time.monotonic() - recorded
                if self.calls > 3:
                    raise RuntimeError('Public probe reached its bounded model-call allowance')
                return http.request(kind, payload, **kwargs)
            def cancel(self, owner):
                return http.cancel(owner)
        counted = CountedClient()
        builder = BoardContextBuilder(fast_system_prompt()+MODEL_HINT)
        maximum = min(768, builder.continuity_capacity())
        assert maximum >= 64
        summary = BoardSummaryClient(counted, board_boot_id=boot,
            final_summary_max_utf8_bytes=maximum, max_calls=3, total_budget_ms=90000)
        worker = BoardMemoryWorker(store, summary, idle=timeline.safe_for_compaction,
                                   compaction_guard_factory=timeline.compaction_guard)
        early_checks = 0
        committed = False
        while time.monotonic()-recorded < 375:
            elapsed = time.monotonic()-recorded
            committed = worker.step()
            if elapsed < 299:
                assert not committed and counted.calls == 0 and store.health()['active_bodies'] == 1
                early_checks += 1
            status = dict(stage='SUMMARY_COMMITTED' if committed else 'WAITING_NATURAL_WINDOW',
                          elapsed_seconds=round(time.monotonic()-recorded, 3),
                          active_bodies=store.health()['active_bodies'], model_calls=counted.calls,
                          error=worker.health()['error'], system_time_changed=False)
            (root/'retention-public-progress.json').write_text(json.dumps(status))
            if committed or counted.calls >= 3:
                break
            time.sleep(1)
        result = dict(status='PASS' if committed else 'FAIL', actual_arm=True, real_fixed_27b=True,
            clock='verified_http_date_same_boot_monotonic', board_store_mode='board',
            data='explicit_public_fixture_only', retention_simulated=False,
            early_retention_checks=early_checks, first_model_call_seconds=counted.first_call_seconds,
            elapsed_seconds=round(time.monotonic()-recorded, 3), model_calls=counted.calls,
            worker_error=worker.health()['error'], summary_committed=committed,
            system_time_changed=False, existing_business_database_accessed=False,
            physical_microphone_opened=False, actual_audio_played=False)
        if committed:
            assert counted.first_call_seconds >= 300
            assert store.health()['active_bodies'] == 0
            row = store.history(scope)[0]
            assert row['source'] == 'timeline_summary' and row['detail_available'] is False
            assert all(value in row['text'] for value in ('小林', '3'))
            builder(store.context(scope), '继续讨论刚才的书单。')
            assert builder.metrics['continuity_summary']
            result.update(active_bodies_after_commit=0, summary_utf8_bytes=len(row['text'].encode('utf-8')),
                summary_sha256=hashlib.sha256(row['text'].encode('utf-8')).hexdigest(),
                continuity_selected_with_accepted_persona=True)
            store.forget(scope, event_ids=('public-plan',), operation_id='public-forget-after-summary')
            assert store.history(scope) == [] and store.health()['valid_summaries'] == 0
            result['forget_after_body_cleanup'] = True
        else:
            assert store.health()['active_bodies'] == 1
            result['all_source_bodies_preserved_on_failure'] = True
    signal.alarm(0)
    result['total_seconds'] = round(time.monotonic()-began, 3)
    print(json.dumps(result))
    raise SystemExit(0 if committed else 1)


if __name__ == '__main__':
    main()
