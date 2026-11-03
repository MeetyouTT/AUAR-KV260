"""Independent local review: immutable candidate inputs, public synthetic fixtures only."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'identity_dialogue_collaboration'
manifest_raw=(SOURCE/'SOURCE_MANIFEST.json').read_bytes();manifest=json.loads(manifest_raw)
baseline=SOURCE/'baseline';candidate=SOURCE/'candidate'
for relative,row in manifest['baseline_files'].items():
    assert hashlib.sha256((baseline/relative).read_bytes()).hexdigest()==row['sha256'],relative
changed='tools/unified_identity_binding.py'
before=(baseline/changed).read_bytes();after=(candidate/changed).read_bytes()
assert hashlib.sha256(before).hexdigest()==manifest['files'][changed]['before_sha256']=='f083fe8b618f4b09dce1587b3c32bf47f92510948e728615ce989ef31a1757cf'
candidate_sha=hashlib.sha256(after).hexdigest()
assert candidate_sha==manifest['files'][changed]['sha256']=='a94ffd53a1b0e9d8ea8843f55fdf5543fdf6a5b1410da2f41804bda82220b029'
assert {str(p.relative_to(candidate)).replace('\\','/') for p in candidate.rglob('*.py')}=={changed}
recorded=json.loads((HERE.parent/'parallel_platform/gui_startup_review/gui_bootstrap_01.json').read_text(encoding='utf-8'))['board_result']
startup_path='/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json'
pins=json.loads(recorded['files'][startup_path]['text'])['component_sha256']
review_paths=(changed,'common/voice_enrollment.py','tools/provisional_voice.py','tools/binding_hub_runtime.py',
    'board/runtime/board_speaker_business.py','common/identity_links.py','common/binding_api.py')
assert all(manifest['baseline_files'][p]['sha256']==pins[p] for p in review_paths)
base_ast=ast.parse(before.decode());new_ast=ast.parse(after.decode())
patched=copy.deepcopy(new_ast)
klass=next(n for n in patched.body if isinstance(n,ast.ClassDef) and n.name=='UnifiedBindingRouter')
route=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='route')
voice=next(n for n in ast.walk(route) if isinstance(n,ast.If) and ast.unparse(n.test)=="state == 'SAMPLING_VOICE'")
assert isinstance(voice.body[0],ast.ImportFrom) and voice.body[0].module=='common.voice_enrollment'
assert [a.name for a in voice.body[0].names]==['identity_query_requested']
assert ast.unparse(voice.body[1])=="if identity_query_requested(text):\n    return self.decision('ordinary', reason='IDENTITY_QUERY_DURING_VOICE_ENROLLMENT')"
voice.body=voice.body[2:]
assert ast.dump(patched,include_attributes=False)==ast.dump(base_ast,include_attributes=False)

sys.path.insert(0,str(baseline))
import common,tools
common.__path__=[str(baseline/'common')]
tools.__path__=[str(candidate/'tools'),str(baseline/'tools')]
spec=importlib.util.spec_from_file_location('review_public_identity_fixtures',SOURCE/'test_identity_query_isolation.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
buffer=io.StringIO()
result=unittest.TextTestRunner(verbosity=2,stream=buffer).run(unittest.defaultTestLoader.loadTestsFromModule(fixtures))
with (HERE/'INDEPENDENT_QUERY_TESTS.log').open('x',encoding='utf-8') as stream:stream.write(buffer.getvalue())
from common.voice_enrollment import identity_query_requested
from tools.provisional_voice import query_reply
extra=[]
for phrase in ('听声音我是谁','你认识我的声音吗'):
    meta,scene,registry,speaker,hub=fixtures.hub_fixture()
    before_stage=copy.deepcopy(speaker.sessions[hub.router.actor(meta)]['stage'])
    response=hub.route(meta,phrase,fixtures.PCM,visual=scene)
    extra.append({'phrase':phrase,'original_hub_query_predicate_accepts':query_reply(phrase,{'state':'UNKNOWN'}) is not None,
        'new_router_predicate_accepts':identity_query_requested(phrase),
        'actual_decision_route':response['decision']['route'],'actual_decision_reason':response['decision']['reason'],
        'speaker_turn_call_count':len(speaker.calls),'stage_before':before_stage,
        'stage_after':speaker.sessions[hub.router.actor(meta)]['stage'],
        'original_identity_resolver_call_count':registry.resolve_calls,
        'personal_memory_allowed':response['decision']['personal_memory_allowed']})
assert hashlib.sha256((candidate/changed).read_bytes()).hexdigest()==candidate_sha
audit={'schema':'aura-independent-identity-query-review-1','candidate_sha256':candidate_sha,
    'baseline_sha256':hashlib.sha256(before).hexdigest(),'source_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),
    'all_manifest_baseline_files_verified':len(manifest['baseline_files']),
    'reviewed_dependencies_match_recorded_380_pins':{p:pins[p] for p in review_paths},
    'only_change_is_two_new_AST_nodes_inside_SAMPLING_VOICE':True,
    'provided_test_methods':result.testsRun,'provided_test_failures':len(result.failures),'provided_test_errors':len(result.errors),
    'provided_tests_passed':result.wasSuccessful(),'original_hub_supported_voice_query_edge_cases':extra,
    'candidate_inputs_modified':False,'production_modified':False,'board_accessed':False,
    'private_store_opened':False,'model_or_device_accessed':False}
with (HERE/'INDEPENDENT_AUDIT.json').open('x',encoding='utf-8') as stream:
    json.dump(audit,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({'candidate_sha256':candidate_sha,'test_methods':result.testsRun,'provided_tests_passed':result.wasSuccessful(),
    'edge_cases':extra,'candidate_modified':False,'board_accessed':False},ensure_ascii=False))
