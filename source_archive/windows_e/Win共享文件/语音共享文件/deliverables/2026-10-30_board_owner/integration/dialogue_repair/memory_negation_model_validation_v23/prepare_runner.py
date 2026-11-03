"""Prepare one pinned public model-probe payload locally. Never calls SSH or a model."""
import argparse
import ast
import copy
import importlib.util
import json
from pathlib import Path

import worker


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
V22 = REPAIR / 'release_v22_camera_rebind_candidate'
INPUTS = (REPAIR / 'memory_negation_stability/PUBLIC_MODEL_PROBE_INPUTS.json',
          REPAIR / 'performance_review_newboot/memory_negation_v22_review/PUBLIC_MODEL_ADDITIONS.json')
CAPACITY = REPAIR / 'release_v23_memory_summary_candidate/PRODUCTION_SUMMARY_CAPACITY.json'


def build(mode, selected, candidate_manifest=None, approved_common=None, approved_policy=None):
    raw = (V22 / 'rebind_common.py').read_bytes()
    worker.need(worker.digest(raw) == '40cf3ff5941489ed2151e0feb916188d3f82360c20b2f1ca7e64c15b11963291', 'reviewed_v22_common_changed')
    definition = importlib.util.spec_from_file_location('_v22_public_memory_probe', V22 / 'rebind_common.py')
    common = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(common)
    spec_raw = common.pinned(V22 / 'camera_rebind_evidence/spec.json', worker.SPEC_SHA)
    spec = json.loads(spec_raw)
    worker.need(common.CAMERA == REPAIR / 'jpeg_demand_camera_trial_v21', 'reviewed_sameboot_helper_changed')
    source = common.publisher_remote(spec)
    anchor = "\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    worker.need(source.count(anchor) == 1, 'unique_frozen_dispatch_anchor_required')
    guard_source = source.split(anchor, 1)[0]
    ast.parse(guard_source, feature_version=(3, 9))
    capacity_raw = CAPACITY.read_bytes()
    worker.need(worker.digest(capacity_raw) == '8c4765e2044ad5d66455ce9e414aee954c05ddb7c3dddd04bf5d12580802dd0c', 'production_capacity_evidence_changed')
    worker.need(json.loads(capacity_raw)['production_summary_final_maximum_utf8_bytes'] == 301, 'production_capacity_changed')
    cases, inputs = [], []
    for path in INPUTS:
        raw = path.read_bytes()
        parsed = json.loads(raw)
        worker.need(parsed['public_cases_only'] is True, 'public_input_required')
        inputs.append({'name': path.name, 'sha256': worker.digest(raw)})
        cases.extend({key: copy.deepcopy(case[key]) for key in ('case', 'sources', 'semantic_review_rubric')}
                     for case in parsed['cases'])
    worker.need(len(cases) == 10, 'six_plus_four_public_cases_required')
    cases.append({'case': 'long_repeated_question',
        'sources': [{'source': 'user_said', 'text': '你会不会唱歌？' * 64, 'protected': {}}],
        'semantic_review_rubric': '记录重复询问会不会唱歌，保留提问性质，不把能力写成已确认事实。完整覆盖全部来源及时间范围。实际多段请求次数与reduction以运行metrics为准。'})
    if selected != 'all':
        cases = [case for case in cases if case['case'] == selected]
        worker.need(len(cases) == 1, 'one_known_public_case_required')
    overlays = {}
    if mode == 'candidate':
        worker.need(candidate_manifest is not None and approved_common and approved_policy, 'root_selected_candidate_hashes_required')
        manifest = json.loads(candidate_manifest.read_bytes())
        approved = {'common.board_memory': approved_common, 'board.runtime.board_memory_policy': approved_policy}
        for name, (relative, before_sha) in worker.BEFORE.items():
            record = manifest['sources'][relative]
            path = Path(record['local_source'])
            raw = path.read_bytes()
            worker.need(record['before_sha256'] == before_sha and worker.digest(raw) == record['after_sha256'] == approved[name],
                        'root_selected_two_source_candidate_required')
            ast.parse(raw, feature_version=(3, 9))
            overlays[name] = {'source': raw.decode('utf-8'), 'sha256': approved[name], 'before_sha256': before_sha}
    else:
        worker.need(mode == 'before' and not any((candidate_manifest, approved_common, approved_policy)), 'before_has_no_overlay')
    return {'schema': 'aura.public-memory-model-probe.v23', 'public_cases_only': True, 'mode': mode,
        'spec_raw': spec_raw.decode('utf-8'), 'guard_source': guard_source, 'guard_sha256': worker.digest(guard_source.encode()),
        'final_summary_max_utf8_bytes': 301, 'capacity_evidence_sha256': worker.digest(capacity_raw),
        'cases': cases, 'public_fixture_sources': inputs, 'candidate_sources': overlays,
        'old_prompt_messages_copied': False, 'device_or_model_accessed_during_preparation': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('before', 'candidate'), default='before')
    parser.add_argument('--case', default='question_will')
    parser.add_argument('--candidate-manifest', type=Path)
    parser.add_argument('--approved-common-sha256')
    parser.add_argument('--approved-policy-sha256')
    parser.add_argument('--write-payload', type=Path)
    args = parser.parse_args()
    payload = build(args.mode, args.case, args.candidate_manifest, args.approved_common_sha256, args.approved_policy_sha256)
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if args.write_payload:
        with args.write_payload.open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'status': 'LOCAL_PUBLIC_PAYLOAD_PREPARED_NO_MODEL_OR_DEVICE_ACCESS', 'mode': args.mode,
        'cases': [case['case'] for case in payload['cases']], 'payload_sha256': worker.digest(raw),
        'bytes': len(raw), 'written': bool(args.write_payload), 'worker_sha256': worker.digest((HERE / 'worker.py').read_bytes())}))


if __name__ == '__main__':
    main()
