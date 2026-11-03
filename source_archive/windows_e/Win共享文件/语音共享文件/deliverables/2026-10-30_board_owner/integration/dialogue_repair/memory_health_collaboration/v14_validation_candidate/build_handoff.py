import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
baseline = json.loads((HERE/'baseline_sources.json').read_text(encoding='utf-8'))
files = {}
for name in ('common/board_memory.py', 'board/runtime/board_memory_policy.py'):
    path = HERE/'after'/name
    ast.parse(path.read_text(encoding='utf-8'))
    files[name] = dict(path='after/'+name, before_sha256=baseline[name]['before_sha256'],
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
tests = {}
for mode in ('baseline','targeted','regression'):
    path = HERE/('test_'+mode)/'results.xml'
    suite = ET.parse(path).find('testsuite')
    tests[mode] = {key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')}
    tests[mode]['passed'] = tests[mode]['tests']-tests[mode]['failures']-tests[mode]['errors']-tests[mode]['skipped']
    tests[mode]['seconds'] = float(suite.attrib['time'])
    tests[mode]['evidence'] = str(path.relative_to(HERE))
script = HERE/'board_readonly_metadata_v14.py'
value = dict(schema='aura.memory-protected-validation-candidate.v1',
    status='SOURCE_ONLY_READY_FOR_ROOT_REVIEW', baseline_startup_sha256=baseline['startup_sha256'], files=files,
    unchanged_backoff_sha256=baseline['common/board_memory_backoff.py']['before_sha256'],
    atomic_source_update_required=True,
    deployment_note='Install both source modules together; policy imports the typed reason constant. Root is sole publisher; recheck latest actual module hashes before merge.',
    readonly_script=dict(path=script.name, sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
        suitable_on_v13=True, sql_mode='ro+query_only', vm_budget_seconds=.4,
        outputs=['Fixed rejection enums when available', 'Aggregate task attempt buckets', 'Backlog source counts', 'Existing metadata only'],
        calls_inference=False, imports_production=False), tests=tests,
    changes=[
        'CandidateRejected carries at most seven static rejection reason enums; no exception text parsing or source values exported',
        'Same original validation predicates now report all failing categories; Store/worker/permission/transaction functions are AST-identical',
        'Exact known board camera person-count event schema can render a compact count-only summary without LLM; no user speech, extra fields or unknown producer text accepted',
        'Structured candidate still passes original full-source validation, claims/refs/cutoff/lease/generation checks and atomic Store commit; unsupported events use unchanged LLM path'],
    structured_contract=dict(scope='device', topic='视觉', source='camera_observed',
        time_basis='board_camera_health_source_bound', evidence='visual_observation', speaker_known=False,
        producer_claim_fields=['event_kind','people_count','source_frame_id','source_kind'],
        source_kind='actual', count_range=[0,1000],
        limits='Exact existing producer sentences plus consistent integer numbers/claims; no extra metadata or claims; output must fit existing final summary capacity',
        narrative='Counts from typed sources in recording order; 0 means a sample did not detect a body; no arrival/departure/identity/continuous-presence claims',
        transcript_archive=False, model_calls_for_recognized_records=0),
    queue_findings=dict(attempts_four_is_cap=False,
        meaning='Identical task retry count; source selection prefers the maximum previous source attempt count, then age. No four-attempt discard or quarantine.',
        worker_wide_cooldown='Real failures delay every partition up to 60 seconds',
        different_partitions='Fewer-attempt groups can progress after cooldown; not a permanent global head-of-line lock',
        same_atomic_segment='A poison source can repeatedly retain a healthy companion; five synthetic attempts reproduce this without deleting either body',
        queue_code_changed=False),
    actual_findings=dict(evidence='../actual_metadata_v13_initial.json', historical_committed=270,
        current_worker_rejections=6, observed_stage='full_source_validation', backlog_events=796,
        missing_body_expected_migrated_command=1, missing_body_unexplained=0,
        exact_v13_rejection_reason='Not recoverable from old four-field diagnostics; no model text was archived. New fixed enums reveal future rejections.',
        prior_wording_example='Synthetic source-derived camera wording can omit metadata numeral 0 and fail the original observation marker regex; this reproduces possible causes without claiming they were the six real responses.'),
    guarantees=['No validation predicate removed or weakened', 'No business data replay/migration/schema change',
        'No premature body deletion or raw archive', 'No new model/service/writer',
        'Original same-boot generation fix, backoff, deadlines and source/permission guards preserved'],
    limitations=['Free-form LLM summaries still cannot be mechanically proven semantically lossless; rejected candidates stay pending',
        'Queue scheduling and global backoff unchanged; residual poison batches may need a later separate remedy',
        'Actual new rejection codes, eligible camera backlog size and postdeployment progress require root-only metadata'],
    production_modified=False, real_models_called=False, board_connected=False)
assessment_path = HERE/'ACTUAL_PROGRESS_ASSESSMENT.json'
if assessment_path.is_file():
    assessment = json.loads(assessment_path.read_text(encoding='utf-8'))
    latest = assessment.get('latest_observation', {})
    value['status'] = 'ROOT_DEPLOYED_V14_STRUCTURED_CAMERA_NET_BACKLOG_REDUCTION_VERIFIED'
    value['v13_problem_baseline'] = value.pop('actual_findings')
    value['root_deployment'] = dict(startup_sha256=assessment['startup_sha256'],
        root_published=True, candidate_modules_match=assessment['candidate_modules_match'],
        analysis='ACTUAL_PROGRESS_ASSESSMENT.json', latest=latest,
        comparison=assessment.get('followup_comparison'),
        overall='Structured camera publication and short-window net backlog reduction verified; all-library health, free-form summaries and backlog clearance not verified')
    value['action_scope_note'] = 'production_modified/real_models_called/board_connected false refer to this collaborating conversation; root performed the recorded deployment and diagnostic reads.'
(HERE/'HANDOFF.json').write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status=value['status'], files=files, tests=tests), ensure_ascii=True))
