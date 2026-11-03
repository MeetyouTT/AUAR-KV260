"""Root-only one-pair diagnostic, dry by default, with no persistent product edits."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys
import time
import types


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
R2 = HERE.parent / 'failed_summary_shape_v23/r2_bytes_uri'
CANDIDATE = REPAIR / 'memory_negation_v24_candidate'
BASE_WORKER_SHA = 'bcba117592f2f1c1966c45c69784b815bd68277e6d8ac6066194e0f7a5745c70'
CANDIDATE_SHA = '80de72bce6d816a4da52db1dadee4a2c27c5c59242a1929c6316b76071c3105a'


def inputs():
    import hashlib
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(R2 / 'HANDOFF.json') != '52dc3cf8571176de44ad34f600a5a0defc12c08c94267b4ad87c6e944a866f62':
        raise ValueError('frozen_r2_changed')
    handoff = json.loads((R2 / 'HANDOFF.json').read_bytes())
    for name, row in handoff['files'].items():
        if digest(R2 / name) != row['sha256']:
            raise ValueError('frozen_r2_file_changed')
    definition = importlib.util.spec_from_file_location('_frozen_r2_ab_inputs', R2 / 'run_diagnose.py')
    previous = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(previous)
    common, arguments, base_source = previous.inputs()
    common.need(common.sha(base_source.encode()) == BASE_WORKER_SHA, 'exact_r2_worker_required')
    manifest = json.loads(common.pinned(CANDIDATE / 'SOURCE_MANIFEST.json',
        '0d8cefe2d42f163fa6c4fefcc7a7e8ac472f3265a5d30baecdf052050a9196a3'))
    common.need(set(manifest['sources']) == {'board/runtime/board_memory_policy.py'}, 'policy_only_candidate_required')
    row = manifest['sources']['board/runtime/board_memory_policy.py']
    candidate = common.pinned(row['local_source'], CANDIDATE_SHA)
    arguments.update(candidate_source=candidate.decode('utf8'), candidate_sha256=CANDIDATE_SHA)
    base = types.ModuleType('base_worker')
    exec(compile(base_source, '<frozen-r2-worker>', 'exec'), base.__dict__)
    sys.modules['base_worker'] = base
    definition = importlib.util.spec_from_file_location('_local_ab_contract', HERE / 'ab_worker.py')
    contract = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(contract)
    original = common.pinned(REPAIR / 'memory_negation_v23_candidate_r4/after/board/runtime/board_memory_policy.py', contract.BASE_POLICY)
    contract.reviewed_messages(original, candidate)
    body = (HERE / 'ab_worker.py').read_text(encoding='utf8')
    source = "import sys,types\nbase=types.ModuleType('base_worker')\nsys.modules['base_worker']=base\nexec(compile(" + repr(base_source) + ",'<frozen-r2-worker>','exec'),base.__dict__)\n" + body
    ast.parse(source, feature_version=(3, 9))
    remote = previous.REMOTE.replace('timeout=45', 'timeout=90')
    common.need(remote.count('timeout=90') == 1, 'one_owned_child_90_second_window_required')
    # The public JSON parser stays the exact frozen R2 strict parser.
    remote = remote.replace("contract['parse'](output)", "contract['base'].parse(output)")
    return common, arguments, source, remote, contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    common, arguments, source, remote, contract = inputs()
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_SAME_SNAPSHOT_AB_VALIDATED', maximum_model_calls=2,
                              per_arm_budget_ms=30000, hard_window_seconds=90, component_count=380)))
        return
    handoff = json.loads((HERE / 'HANDOFF.json').read_bytes())
    for name, row in handoff['files'].items():
        common.pinned(HERE / name, row['sha256'])
    result = common.execute_remote(remote, dict(WORKER_SOURCE=source, ARGUMENTS=arguments), timeout=110)
    contract.validate_output(result)
    common.write_new_json(HERE / ('actual_pair_' + str(time.time_ns()) + '.json'), result)
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
