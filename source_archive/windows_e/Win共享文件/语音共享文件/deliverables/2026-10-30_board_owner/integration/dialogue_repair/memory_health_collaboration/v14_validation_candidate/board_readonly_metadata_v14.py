"""Root publisher runs on KV260: fixed metadata only, no production imports.

Read-only /api/state and SQLite mode=ro, query_only, bounded VM execution.
Never opens devices, calls inference, writes a store, or emits text/IDs/errors.
Optional argv[1] pins the expected current startup SHA; repin after a release.
"""
import collections
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
DATABASE = Path('/home/root/.local/share/aura-board-business/timeline.sqlite3')
ERROR_CODES = frozenset(('', 'none', 'operation_failed', 'dialogue_preempted', 'lease_expired',
    'source_changed', 'scope_cleared', 'candidate_rejected', 'model_failed', 'database_busy',
    'cancelled', 'deadline_exceeded', 'clock_unverified', 'compaction_failed',
    'context_limit', 'preempted', 'superseded', 'foreground_busy', 'backend_failed',
    'backend_invalid_result', 'gpu_busy', 'startup_busy', 'queue_full', 'owner_capacity',
    'duplicate_request', 'stale_generation', 'shutdown', 'tts_owner_conflict', 'tts_ownership_unavailable'))
STATES = frozenset(('leased', 'committed', 'failed', 'cancelled', 'expired'))
REJECTION_REASONS = ('protected_name_missing', 'protected_number_missing_or_changed',
    'negation_missing', 'planned_status_missing', 'completed_status_missing',
    'cancelled_status_missing', 'observation_evidence_missing')
SOURCE_FILES = ('common/board_memory.py', 'common/board_memory_backoff.py',
    'board/runtime/board_memory_policy.py', 'board/runtime/board_dialogue_client.py',
    'board/runtime/board_business.py', 'tools/production_memory_presentation.py',
    'common/board_timeline_clock.py')


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def error_code(value):
    return 'none' if value is None else value if isinstance(value, str) and value in ERROR_CODES else 'other'


def fixed_numbers(value, keys):
    value = value if isinstance(value, dict) else {}
    return {key: number(value.get(key)) for key in keys}


def missing_body_metadata(db):
    """Separate a known bodyless migration marker from unexplained absence.

    A valid user event can intentionally be metadata-only when a migrated
    explicit-memory command was excluded from raw recall but remains the
    source of an imported current fact. Require all those links; no inference
    from IDs, private metadata or the event text is made here.
    """
    missing = (" FROM bm_events e LEFT JOIN bm_bodies b USING(event_id) "
        "WHERE e.state='valid' AND b.event_id IS NULL AND e.compacted_summary_id IS NULL")
    total = db.execute('SELECT COUNT(*)' + missing).fetchone()[0]
    needed = ('bm_migration_turn_map', 'bm_migration_exclusions', 'bm_migrations')
    available = all(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
                    for name in needed)
    known = 0
    if available:
        condition = (" AND e.source='user_said' AND e.provenance_complete=1 AND EXISTS("
            "SELECT 1 FROM bm_migration_turn_map m JOIN bm_migration_exclusions x "
            "ON x.import_id=m.import_id AND x.source_seq=m.source_seq "
            "JOIN bm_migrations z ON z.import_id=m.import_id "
            "WHERE m.user_event_id=e.event_id AND z.state='complete' "
            "AND x.reason_code IN ('memory_command','personal_memory_command','memory_controls_command')) "
            "AND EXISTS(SELECT 1 FROM bm_fact_sources fs JOIN bm_facts f "
            "ON f.scope_kind=fs.scope_kind AND f.scope_id=fs.scope_id AND f.fact_key=fs.fact_key "
            "AND f.revision=fs.revision WHERE fs.event_id=e.event_id AND f.state='current')")
        known = db.execute('SELECT COUNT(*)' + missing + condition).fetchone()[0]
    return dict(total=total, migration_proof_tables_present=available,
        migrated_excluded_command_with_current_fact=known, unexplained=total-known,
        classification_uses_text_or_private_identifiers=False)


def diagnose(root=ROOT, database=DATABASE, expected_sha=None, state_loader=None):
    result = dict(metadata_only=True, read_only=True, model_calls=0,
        production_modules_imported=False, observed_mono=time.monotonic())
    startup = root / 'startup/config.json'
    result['startup_sha256'] = hashlib.sha256(startup.read_bytes()).hexdigest()
    if expected_sha is not None:
        if re.fullmatch('[0-9a-f]{64}', expected_sha) is None:
            raise ValueError()
        result['expected_startup_matches'] = expected_sha == result['startup_sha256']
        if not result['expected_startup_matches']:
            result['diagnostic_status'] = 'version_changed_repin_before_read'
            return result
    if state_loader is None:
        connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=2)
        try:
            connection.request('GET', '/api/state')
            response = connection.getresponse()
            raw = response.read(1048577)
            if response.status != 200 or len(raw) > 1048576:
                raise ValueError()
            state = json.loads(raw)
        finally:
            connection.close()
    else:
        state = state_loader()
    business = state.get('board_business', {})
    memory = business.get('memory', {})
    retry = memory.get('retry_backoff', {})
    clock = business.get('clock', {})
    result['worker'] = dict(running=memory.get('running') is True,
        error_code=error_code(memory.get('error')), **fixed_numbers(memory, ('completed', 'discarded')))
    result['retry'] = dict(last_failure_code=error_code(retry.get('last_failure_code')),
        **fixed_numbers(retry, ('failure_streak', 'retry_in_seconds', 'last_delay_seconds')))
    diagnostics = memory.get('summary_diagnostics', {})
    stages = {'idle', 'prepare', 'admission', 'model_request', 'wire_response', 'semantic_json',
        'semantic_shape', 'semantic_bounds', 'fragmentation', 'fragment_validation', 'reduction',
        'reduction_validation', 'full_source_validation', 'complete', 'structured_camera_counts'}
    classes = {'none', 'InterruptedError', 'TimeoutError', 'RuntimeError', 'ValueError', 'CandidateRejected',
        'ContextLimitError', 'ModelRequestError', 'WireError', 'MemoryBusy', 'ClockUnavailable', 'OSError',
        'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError', 'JSONDecodeError', 'TypeError',
        'KeyError', 'AttributeError', 'AssertionError', 'NameError', 'NotImplementedError', 'OperationalError', 'DatabaseError'}
    if isinstance(diagnostics, dict) and diagnostics:
        result['summary_diagnostics'] = dict(
            state=diagnostics.get('state') if diagnostics.get('state') in ('idle', 'complete', 'deferred', 'failed') else 'other',
            stage=diagnostics.get('stage') if diagnostics.get('stage') in stages else 'other',
            code=error_code(diagnostics.get('code')),
            error_class=diagnostics.get('error_class') if diagnostics.get('error_class') in classes else 'other')
        reasons = diagnostics.get('rejection_reasons')
        if isinstance(reasons, (tuple, list)):
            result['summary_diagnostics']['rejection_reasons'] = [code for code in REJECTION_REASONS if code in reasons]
        if diagnostics.get('method') == 'structured_camera_counts':
            result['summary_diagnostics']['method'] = 'structured_camera_counts'
    result['clock'] = dict(safe_for_compaction=clock.get('safe_for_compaction') is True,
        **fixed_numbers(clock, ('utc_lower_bound', 'uncertainty_seconds', 'verified_age_seconds')))
    result['retention_enabled'] = business.get('retention', {}).get('enabled') is True
    result['source_sha256'] = {}
    for relative in SOURCE_FILES:
        path = root / 'runtime/aura' / relative
        result['source_sha256'][relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if not database.is_file() or database.is_symlink() or database.resolve() != database:
        raise ValueError()
    start = time.monotonic()
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=.15)
    db.set_progress_handler(lambda: int(time.monotonic() - start > .4), 500)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        grouped = collections.Counter()
        for status, code, count in db.execute(
                'SELECT status,error_code,COUNT(*) FROM bm_tasks GROUP BY status,error_code'):
            grouped[(status if status in STATES else 'other', error_code(code))] += count
        result['task_counts'] = [dict(state=s, error_code=e, count=n) for (s, e), n in sorted(grouped.items())]
        recent = collections.Counter()
        for status, code in db.execute('SELECT status,error_code FROM bm_tasks ORDER BY created_utc DESC LIMIT 16'):
            recent[(status if status in STATES else 'other', error_code(code))] += 1
        result['latest_16_task_counts'] = [dict(state=s, error_code=e, count=n) for (s, e), n in sorted(recent.items())]
        attempts = collections.Counter()
        for status, code, bucket, count in db.execute("SELECT status,error_code,CASE "
                "WHEN attempts=1 THEN '1' WHEN attempts=2 THEN '2' WHEN attempts=3 THEN '3' "
                "WHEN attempts=4 THEN '4' ELSE '5_plus' END AS bucket,COUNT(*) FROM bm_tasks GROUP BY status,error_code,bucket"):
            attempts[(status if status in STATES else 'other', error_code(code), bucket)] += count
        result['task_attempt_buckets'] = [dict(state=s, error_code=e, attempts_bucket=b, count=n)
            for (s,e,b),n in sorted(attempts.items())]
        def scalar(sql, args=()):
            return db.execute(sql, args).fetchone()[0]
        result['store'] = dict(active_bodies=scalar('SELECT COUNT(*) FROM bm_bodies'),
            valid_summaries=scalar("SELECT COUNT(*) FROM bm_summaries WHERE state='valid'"),
            invalidated_summaries=scalar("SELECT COUNT(*) FROM bm_summaries WHERE state='invalidated'"),
            open_turns=scalar("SELECT COUNT(*) FROM bm_turns WHERE status IN ('generating','awaiting_playback')"),
            maximum_task_attempts=scalar('SELECT COALESCE(MAX(attempts),0) FROM bm_tasks'),
            compacted_bodies_remaining=scalar('SELECT COUNT(*) FROM bm_bodies b JOIN bm_events e USING(event_id) '
                'WHERE e.compacted_summary_id IS NOT NULL'),
            invalidated_summary_payloads_remaining=scalar("SELECT COUNT(*) FROM bm_summaries WHERE state='invalidated' "
                "AND (summary IS NOT NULL OR keywords!='[]' OR claims!='[]')"),
            unlinked_missing_valid_bodies=scalar("SELECT COUNT(*) FROM bm_events e LEFT JOIN bm_bodies b USING(event_id) "
                "WHERE e.state='valid' AND b.event_id IS NULL AND e.compacted_summary_id IS NULL"))
        result['missing_body_classification'] = missing_body_metadata(db)
        lower = number(clock.get('utc_lower_bound'))
        result['count_time_basis'] = 'board_stable_clock_utc_lower_bound'
        if lower is not None:
            cutoff = lower - 300
            ready = (" FROM bm_events e JOIN bm_bodies b USING(event_id) LEFT JOIN bm_turns t ON t.turn_id=e.turn_id "
                "WHERE e.state='valid' AND e.closed_utc<=? AND (e.turn_id IS NULL OR t.closed_utc<=?)")
            oldest = scalar('SELECT MIN(e.closed_utc)' + ready, (cutoff, cutoff))
            committed = scalar("SELECT MAX(s.created_utc) FROM bm_summaries s JOIN bm_tasks t ON t.summary_id=s.summary_id "
                "WHERE t.status='committed'")
            result['store'].update(backlog_events=scalar('SELECT COUNT(*)' + ready, (cutoff, cutoff)),
                oldest_backlog_age_seconds=max(0, lower-oldest) if oldest is not None else 0,
                last_commit_age_seconds=max(0, lower-committed) if committed is not None else None,
                active_leases=scalar("SELECT COUNT(*) FROM bm_tasks WHERE status='leased' AND lease_until>?", (lower,)),
                expired_leases=scalar("SELECT COUNT(*) FROM bm_tasks WHERE status='leased' AND lease_until<=?", (lower,)))
            sources = collections.Counter()
            allowed_sources = {'user_said', 'assistant_reply', 'assistant_played', 'camera_observed', 'device_event', 'memory_command'}
            for source, count in db.execute('SELECT e.source,COUNT(*)' + ready + ' GROUP BY e.source', (cutoff,cutoff)):
                sources[source if source in allowed_sources else 'other'] += count
            result['backlog_source_counts'] = [dict(source=s, count=n) for s,n in sorted(sources.items())]
        result['diagnostic_status'] = 'metadata_read_complete'
    finally:
        db.close()
    result['read_elapsed_ms'] = round((time.monotonic()-start)*1000, 3)
    return result


if __name__ == '__main__':
    try:
        output = diagnose(expected_sha=sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as exc:
        allowed = {'OperationalError', 'DatabaseError', 'ValueError', 'FileNotFoundError',
            'PermissionError', 'TimeoutError', 'ConnectionRefusedError', 'OSError', 'KeyError', 'TypeError'}
        output = dict(metadata_only=True, read_only=True, diagnostic_status='diagnostic_unavailable',
            error_class=type(exc).__name__ if type(exc).__name__ in allowed else 'other')
    print(json.dumps(output, ensure_ascii=True, allow_nan=False))
