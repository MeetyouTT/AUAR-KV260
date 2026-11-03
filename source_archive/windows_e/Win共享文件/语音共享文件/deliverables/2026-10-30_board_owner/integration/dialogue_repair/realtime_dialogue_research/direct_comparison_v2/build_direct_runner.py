"""Derive a new benchmark from the immutable v1 runner; never edit v1 files."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'first_wait_candidate'
EXPECTED='e5d1f4fe85e2f40ee52cdf52c66e86c0b7e12c0deff47f94525d5a1382d28a36'


def once(text,before,after):
    if text.count(before)!=1: raise ValueError('unexpected_frozen_runner_shape')
    return text.replace(before,after,1)


def build():
    raw=(BASE/'root_abba_benchmark.py').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED: raise ValueError('frozen_v1_runner_changed')
    source=raw.decode('utf-8').replace('\r\n','\n')
    before=source
    lines=source.splitlines(keepends=True)
    nodes=[node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name in {'semantic_math','abba'}]
    for node in sorted(nodes,key=lambda node:node.lineno,reverse=True):
        lines[node.lineno-1:node.end_lineno]=[]
    source=''.join(lines)
    source=once(source,"ROOT = Path(__file__).resolve().parent\nsys.path.insert(0, str(ROOT))\nfrom build_candidate import AURA, PROJECT, SOURCES\n\nQUESTION = '请只给结果：六乘九等于多少？'",
        "ROOT = Path(__file__).resolve().parent\nBASE = ROOT.parent/'first_wait_candidate'\nsys.path[:0] = [str(ROOT),str(BASE)]\nfrom build_candidate import AURA, PROJECT, SOURCES\nfrom direct_logic import QUESTION, abba, model_messages")
    source=source.replace("ROOT/'BENCH_DEPENDENCY_PINS.json'","BASE/'BENCH_DEPENDENCY_PINS.json'")
    source=source.replace("ROOT/'candidate/","BASE/'candidate/").replace("ROOT/'after/","BASE/'after/")
    source=once(source,"validator_path = ROOT.parents[2]/","validator_path = BASE.parents[2]/")
    old="""    if args.family == 'compact_schema':
        adapter_module = load('research_benchmark_adapter', BASE/'candidate/compact_request_adapter.py')
        prompt = adapter_module.CompactRequestAdapter(object(), system_prompt=prompt,
            capabilities={'format_contract_version':1,'output_formats':list(contract.FORMATS)}).translated_prompt
        candidate = 'dialogue_abc_v1'
        decoder = contract.canonicalize_compact
    else:
        candidate, decoder = 'dialogue_schema_v1', lambda text:text
"""
    new="""    adapter_module = load('research_benchmark_adapter', BASE/'candidate/compact_request_adapter.py')
    compact_prompt = adapter_module.CompactRequestAdapter(object(), system_prompt=prompt,
        capabilities={'format_contract_version':1,'output_formats':list(contract.FORMATS)}).translated_prompt
    candidate = 'dialogue_abc_v1'
    def decoder(text, arm):
        return contract.canonicalize_compact(text) if arm == 'B' else text
"""
    source=once(source,old,new)
    source=once(source,"        count += 1\n        payload = wire.validate_request('llm',",
        "        count += 1\n        selected_messages = model_messages(mode, selected_messages, prompt, compact_prompt)\n        payload = wire.validate_request('llm',")
    source=once(source,"    rows = abba(infer,guard,messages=messages,candidate=candidate,validate_reply=validate_model_reply,\n                decode_reply=decoder,cycles=args.cycles)",
        "    study = abba(infer,guard,messages=messages,candidate=candidate,validate_reply=validate_model_reply,\n                decode_reply=decoder,cycles=args.cycles)\n    rows = study['trials']")
    source=once(source,"'schema':'aura.first-wait.public-abba.v1'","'schema':'aura.first-wait.direct-name-abba.v2'")
    source=once(source,"        'same_prompt_seed_budget_across_A_B':True,'same_as_current_production_prompt':args.family=='canonical_schema',",
        "        'same_prompt_seed_budget_across_A_B':False,\n        'same_question_seed_budget_and_sampling':True,'static_contract_names_only_changed':True,\n        'non_system_messages_identical':True,'A_uses_production_static_prompt':True,\n        'B_static_contract_names_rebound_to_abc':True,\n        'exact_speech_comparisons':study['speech_comparisons'],\n        'all_cross_arm_speech_identical':study['all_cross_arm_speech_identical'],")
    source=once(source,"'synthetic_public_question_code':'MUL_6_9_RESULT_ONLY'","'synthetic_public_question_code':'SELF_NAME_DIRECT'")
    source=once(source,"'public_abba_'+uuid.uuid4().hex[:12]","'direct_name_abba_'+uuid.uuid4().hex[:12]")
    source=once(source,"'status':'ROOT_PUBLIC_ABBA_FINISHED'","'status':'ROOT_DIRECT_NAME_ABBA_FINISHED'")
    source=once(source,"choices=('canonical_schema','compact_schema'),default='canonical_schema'",
        "choices=('canonical_to_compact_name',),default='canonical_to_compact_name'")
    source=once(source,"choices=range(1,6),default=1","choices=(1,),default=1")
    source=once(source,"'same_prompt_across_A_B':True,'root_permit_required':True,",
        "'same_prompt_across_A_B':False,'static_contract_names_only_changed':True,\n            'same_question_seed_budget_and_sampling':True,'root_permit_required':True,")
    ast.parse(source)
    (ROOT/'root_direct_name_abba.py').write_text(source,encoding='utf-8',newline='\n')
    delta=''.join(difflib.unified_diff(before.splitlines(keepends=True),source.splitlines(keepends=True),
        fromfile='a/first_wait_candidate/root_abba_benchmark.py',tofile='b/direct_comparison_v2/root_direct_name_abba.py'))
    (ROOT/'direct_name_runner_review.patch').write_text(delta,encoding='utf-8',newline='\n')
    # The service/runner/authority checks are the same frozen code, with ONLY
    # its module-relative source paths redirected to the immutable base.
    def function(text,name):
        return next(node for node in ast.parse(text).body if isinstance(node,ast.FunctionDef) and node.name==name)
    for name in ('fetch','selected_static_prompt','load'):
        if ast.dump(function(source,name))!=ast.dump(function(before,name)):
            raise ValueError('guard_helper_changed')
    execute_before=function(before,'execute')
    execute_after=function(source,'execute')
    def guard(node):
        return next(child for child in node.body if isinstance(child,ast.FunctionDef) and child.name=='guard')
    if ast.dump(guard(execute_before))!=ast.dump(guard(execute_after)):
        raise ValueError('runtime_guard_changed')
    print(json.dumps({'status':'NEW_DIRECT_NAME_RUNNER_BUILT_FROZEN_V1_UNCHANGED',
        'runner_sha256':hashlib.sha256((ROOT/'root_direct_name_abba.py').read_bytes()).hexdigest(),
        'frozen_base_sha256':EXPECTED,'guard_ast_unchanged':True}))


if __name__=='__main__': build()
