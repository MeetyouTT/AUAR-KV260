"""Summarize isolated source/test evidence; never opens production data."""
import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE/'baseline_sources.json').read_text(encoding='utf-8'))
live_manifest = json.loads((HERE.parent/'frontend_balance_candidate/baseline_manifest.json').read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = {}
for relative in ('board/runtime/board_memory_policy.py', 'common/board_memory_backoff.py'):
    target = HERE/'after'/relative
    ast.parse(target.read_text(encoding='utf-8'))
    files[relative] = dict(path='after/'+relative, before_sha256=manifest[relative]['sha256'],
        sha256=digest(target), bytes=target.stat().st_size,
        frozen_baseline_matches_v10_manifest=manifest[relative]['sha256'] == live_manifest['component_sha256'][relative])
tests = {}
for mode in ('baseline', 'baseline_restart', 'baseline_regression', 'candidate', 'regression'):
    file = HERE/('test_'+mode)/'results.xml'
    suite = ET.parse(file).find('testsuite')
    counts = {key: int(suite.attrib.get(key, 0)) for key in ('tests', 'failures', 'errors', 'skipped')}
    counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    counts['seconds'] = float(suite.attrib['time'])
    counts['evidence'] = str(file.relative_to(HERE))
    tests[mode] = counts
handoff = dict(schema='aura.memory-health-collaboration.v1', status='SOURCE_ONLY_CANDIDATE_READY_ACTUAL_DIAGNOSIS_PENDING',
    baseline_startup_sha256=live_manifest['startup_sha256'],
    baseline_source_manifest_sha256=live_manifest['source_manifest_sha256'], files=files,
    unchanged_store_sha256=manifest['common/board_memory.py']['sha256'],
    readonly_script=dict(path='board_readonly_metadata.py', sha256=digest(HERE/'board_readonly_metadata.py'),
        invocation='python3 -B - <CURRENT_STARTUP_SHA256>  (send script on stdin from root publisher)',
        source_root='ROOT/runtime/aura', fixed_fields_only=True, sqlite_mode='ro', query_only=True,
        sqlite_busy_seconds=.15, sqlite_vm_budget_seconds=.4, state_timeout_seconds=2,
        clock_time_basis='business.clock.utc_lower_bound; identical to StableTimelineClock.event_time',
        models_called=0, tests='tests/test_metadata_script.py'), tests=tests,
    confirmed_defects=[
        'Same-boot board runtime restart resets generation to 1 for constant memory-worker session; persistent inference host rejects stale_generation after prior calls',
        'Remote structured preemption/foreground-busy codes become model_failed when local cancellation is false',
        'Remote structured deadline_exceeded becomes model_failed',
        'Public error presentation/probe suppress diagnostic distinction; new reader emits allowlisted reason enums'],
    candidate_behavior=[
        'Seed/advance request generation from same-boot monotonic microsecond ordinal; keep constant transport owner slot, original stale-generation guard and wire bound',
        'cancelled/preempted/superseded/foreground_busy replies raise InterruptedError; original wrapper does not increment failure streak',
        'Remote deadline_exceeded raises TimeoutError; original retry policy remains bounded',
        'True backend failures remain model_failed; invalid JSON/schema/protected-field omission remain rejected',
        'Summary diagnostic snapshot contains fixed stage/code/exception-class enums only, exposed through existing worker health'],
    preserved=['Store/schema/leases/transaction boundaries', 'Atomic summary/readback/body-delete transaction',
        'All source coverage and semantic checks', 'Five-minute cutoff and incomplete-turn protection',
        'Scope/grant/generation/revision checks', 'Fresh read transaction on every output packet',
        'Original model/deadline/context budgets and backoff maximum', 'No new service, model or database writer'],
    rollback_note='Keep generation fix if reverting other code while Windows host survives; resetting counter to 1 becomes stale again. Minimal retained hunk: rollback_safe/generation_only.patch. Never restore a business database or restart models as an implicit rollback.',
    test_scope=dict(synthetic_sqlite=True, fake_model_responses=True, real_models=False,
        real_audio=False, real_database=False, board_access=False, localhost_fake_http_only=True,
        stale_character_fixtures='Three unmodified retired-character tests fail on baseline too; retained separately, explicitly deselected in final regression; three selected-character equivalents pass',
        windows_skip='POSIX private-mode check; Windows uses caller ACL'),
    actual_production_conclusion='V11 read shows 270 historical successful summaries, 622 pending events and about 53 minutes since last commit. Exact current model_failed subtype and one valid bodyless event remain unverified; root-only updated readonly proof counts and candidate stage telemetry are ready.',
    production_modified=False, model_calls=0)
actual_path = HERE/'actual_metadata_v11.json'
if actual_path.is_file():
    actual = json.loads(actual_path.read_text(encoding='utf-8-sig'))
    handoff['actual_baseline'] = dict(evidence=actual_path.name, startup_sha256=actual['startup_sha256'],
        candidate_bases_match=all(value['before_sha256'] == actual['source_sha256'].get(relative) for relative, value in files.items()),
        store_base_matches=handoff['unchanged_store_sha256'] == actual['source_sha256'].get('common/board_memory.py'),
        historical_committed_tasks=270, valid_summaries=actual['store']['valid_summaries'],
        backlog_events=actual['store']['backlog_events'], last_commit_age_seconds=actual['store']['last_commit_age_seconds'])
(HERE/'HANDOFF.json').write_text(json.dumps(handoff, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status=handoff['status'], candidates=len(files), tests=tests), ensure_ascii=True))
