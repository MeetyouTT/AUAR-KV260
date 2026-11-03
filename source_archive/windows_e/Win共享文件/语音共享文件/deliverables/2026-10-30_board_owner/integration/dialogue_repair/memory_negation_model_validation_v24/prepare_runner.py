"""Build public v24 probe data locally. No device, database or model access."""
import argparse
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys

import worker


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PUBLISHER = REPAIR / 'release_v23_memory_summary_candidate'
OLD_PUBLIC = REPAIR / 'memory_negation_model_validation_v23/candidate_validation_r4/CANDIDATE_R4_ALL_PUBLIC_PAYLOAD.json'
OLD_PUBLIC_SHA = '8a1737c49f7e42c75166dd2d91734168f83328fbcc84a46f6812013580d9e757'
CAPACITY = PUBLISHER / 'PRODUCTION_SUMMARY_CAPACITY.json'
ACTUAL_SOURCES = REPAIR / 'memory_negation_v23_candidate_r4/after'
POLICY_NAME = 'board.runtime.board_memory_policy'
POLICY_RELATIVE = 'board/runtime/board_memory_policy.py'


def common_module():
    raw = (PUBLISHER / 'summary_common.py').read_bytes()
    worker.need(worker.digest(raw) == '7b7227447bee67e38ed4371fc4d58979bdf56f2f36c3745c8fdd934e012d6a25',
                'frozen_v23_publisher_changed')
    definition = importlib.util.spec_from_file_location('_v23_public_memory_probe', PUBLISHER / 'summary_common.py')
    common = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(common)
    return common


def protected_policy(source):
    tree = ast.parse(source, feature_version=(3, 9))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BoardSummaryClient']
    worker.need(len(classes) == 1, 'original_summary_class_required')
    methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == '_messages']
    worker.need(len(methods) == 1, 'single_messages_method_required')
    methods[0].body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def initial_request_plan(cases, policy_source, spec):
    with worker.isolated_project_imports():
        sys.path.insert(0, str(REPAIR / 'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'))
        memory_raw = (ACTUAL_SOURCES / 'common/board_memory.py').read_bytes()
        worker.need(worker.digest(memory_raw) == spec['component_sha256']['common/board_memory.py'], 'actual_memory_source_changed')
        worker.load_overlay('common.board_memory', {'source': memory_raw.decode('utf8')})
        dialogue_path = REPAIR / 'feature_trigger_collaboration/candidate_h01/after/board/runtime/board_dialogue.py'
        dialogue = dialogue_path.read_bytes()
        worker.need(worker.digest(dialogue) == spec['component_sha256']['board/runtime/board_dialogue.py'], 'actual_dialogue_source_changed')
        worker.load_overlay('board.runtime.board_dialogue', {'source': dialogue.decode('utf8')})
        policy = worker.load_overlay(POLICY_NAME, {'source': policy_source})
        summary = policy.BoardSummaryClient(None, board_boot_id='public-memory-v24-plan', final_summary_max_utf8_bytes=301)
        worker.need((summary.maximum, summary.reserve, summary.budget_ms, summary.max_calls, summary.total_budget_ms)
                    == (2048, 384, 30000, 256, 900000), 'production_summary_defaults_changed')
        plan = []
        for case in cases:
            eligible = [dict(event_id='public-plan-' + str(index), revision=1, include_in_summary=True,
                source=row['source'], text=row['text'], metadata=row['protected'], recorded_utc=1700000000.0 + index)
                for index, row in enumerate(case['sources'])]
            records = [dict(source=row['source'], text=row['text'], protected={key: row['metadata'][key]
                for key in ('names', 'numbers', 'negated', 'status', 'evidence') if key in row['metadata']}) for row in eligible]
            if summary._fits(records, multipart=False):
                costs = [policy.message_cost(summary._messages(records), summary.reserve)]
            else:
                summary.metrics = dict(input_utf8_bytes=sum(len(row['text'].encode('utf8')) for row in eligible))
                fragments = summary._fragments(eligible)
                worker.need(summary.metrics['complete_source_coverage'] is True, 'public_source_coverage_required')
                batches = list(summary._batches(fragments))
                costs = [policy.message_cost(summary._messages([row[0] for row in batch], True), summary.reserve)
                         for batch in batches]
            worker.need(costs and max(costs) <= 2048, 'public_initial_request_over_budget')
            plan.append(dict(case=case['case'], initial_requests=len(costs), maximum_initial_message_cost=max(costs)))
        return plan


def build(mode, selected, additions_path, additions_sha, candidate_manifest=None,
          candidate_manifest_sha=None, approved_policy=None):
    common = common_module()
    spec_raw = common.pinned(PUBLISHER / 'memory_summary_evidence/spec.json', worker.SPEC_SHA)
    spec = common.validate_spec(json.loads(spec_raw))
    source = common.publisher_remote(spec)
    anchor = "\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    worker.need(source.count(anchor) == 1, 'unique_frozen_dispatch_anchor_required')
    guard_source = source.split(anchor, 1)[0]
    ast.parse(guard_source, feature_version=(3, 9))
    capacity_raw = common.pinned(CAPACITY, '8c4765e2044ad5d66455ce9e414aee954c05ddb7c3dddd04bf5d12580802dd0c')
    worker.need(json.loads(capacity_raw)['production_summary_final_maximum_utf8_bytes'] == 301, 'capacity_changed')
    old = json.loads(common.pinned(OLD_PUBLIC, OLD_PUBLIC_SHA))
    additions = json.loads(common.pinned(additions_path, additions_sha))
    worker.need(old['public_cases_only'] is True and additions['public_cases_only'] is True
                and len(old['cases']) == 11 and len(additions['cases']) == 4, 'eleven_plus_four_public_cases_required')
    cases = [{key: copy.deepcopy(case[key]) for key in ('case', 'sources', 'semantic_review_rubric')}
             for case in old['cases'] + additions['cases']]
    worker.need(len({case['case'] for case in cases}) == 15, 'distinct_public_cases_required')
    if selected != 'all':
        cases = [case for case in cases if case['case'] == selected]
        worker.need(len(cases) == 1, 'one_known_public_case_required')
    original = common.pinned(ACTUAL_SOURCES / POLICY_RELATIVE, worker.BEFORE[POLICY_NAME][1])
    policy_source = original.decode('utf8')
    overlays = {}
    if mode == 'candidate':
        worker.need(candidate_manifest is not None and candidate_manifest_sha and approved_policy,
                    'root_selected_candidate_policy_required')
        manifest = json.loads(common.pinned(candidate_manifest, candidate_manifest_sha))
        worker.need(set(manifest['sources']) == {POLICY_RELATIVE}, 'policy_only_manifest_required')
        row = manifest['sources'][POLICY_RELATIVE]
        raw = common.pinned(row['local_source'], approved_policy)
        worker.need(row['before_sha256'] == worker.BEFORE[POLICY_NAME][1]
                    and row['after_sha256'] == approved_policy and approved_policy != row['before_sha256'],
                    'selected_policy_hash_required')
        worker.need(protected_policy(raw) == protected_policy(original), 'only_messages_body_may_change')
        policy_source = raw.decode('utf8')
        overlays[POLICY_NAME] = dict(source=policy_source, sha256=approved_policy, before_sha256=row['before_sha256'])
    else:
        worker.need(mode == 'before' and not any((candidate_manifest, candidate_manifest_sha, approved_policy)), 'before_has_no_overlay')
    plan = initial_request_plan(cases, policy_source, spec)
    return dict(schema='aura.public-memory-model-probe.v24', public_cases_only=True, mode=mode,
        spec_raw=spec_raw.decode('utf8'), guard_source=guard_source, guard_sha256=worker.digest(guard_source.encode()),
        final_summary_max_utf8_bytes=301, capacity_evidence_sha256=worker.digest(capacity_raw),
        cases=cases, candidate_sources=overlays, old_prompt_messages_copied=False,
        public_fixture_sources=[dict(path=str(OLD_PUBLIC), sha256=OLD_PUBLIC_SHA),
                                dict(path=str(additions_path), sha256=additions_sha)],
        initial_request_plan=plan, planned_initial_model_calls=sum(row['initial_requests'] for row in plan),
        additional_reduction_requests_depend_on_model_outputs=True,
        production_max_calls_per_case=256, production_total_budget_ms_per_case=900000,
        device_or_model_accessed_during_preparation=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('before', 'candidate'), default='before')
    parser.add_argument('--case', default='all')
    parser.add_argument('--additions', required=True, type=Path)
    parser.add_argument('--additions-sha256', required=True)
    parser.add_argument('--candidate-manifest', type=Path)
    parser.add_argument('--candidate-manifest-sha256')
    parser.add_argument('--approved-policy-sha256')
    parser.add_argument('--write-payload', type=Path)
    args = parser.parse_args()
    payload = build(args.mode, args.case, args.additions, args.additions_sha256, args.candidate_manifest,
                    args.candidate_manifest_sha256, args.approved_policy_sha256)
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8')
    if args.write_payload:
        with args.write_payload.open('xb') as stream:
            stream.write(raw)
    print(json.dumps(dict(status='LOCAL_PUBLIC_V24_PAYLOAD_PREPARED', mode=args.mode,
        cases=len(payload['cases']), planned_initial_model_calls=payload['planned_initial_model_calls'],
        additional_reduction_requests_depend_on_model_outputs=True,
        payload_sha256=worker.digest(raw), bytes=len(raw), written=bool(args.write_payload),
        worker_sha256=worker.digest((HERE / 'worker.py').read_bytes()))))


if __name__ == '__main__':
    main()
