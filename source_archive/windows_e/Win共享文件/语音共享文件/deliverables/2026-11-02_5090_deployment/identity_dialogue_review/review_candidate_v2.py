"""Independent local v2 verification; never writes candidate or production paths."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'identity_dialogue_collaboration'
manifest_raw=(SOURCE/'SOURCE_MANIFEST.json').read_bytes();manifest=json.loads(manifest_raw)
baseline=SOURCE/'baseline';candidate=SOURCE/'candidate';changed='tools/unified_identity_binding.py'
for path,row in manifest['baseline_files'].items():assert hashlib.sha256((baseline/path).read_bytes()).hexdigest()==row['sha256'],path
before=(baseline/changed).read_bytes();after=(candidate/changed).read_bytes()
candidate_sha=hashlib.sha256(after).hexdigest()
assert hashlib.sha256(before).hexdigest()==manifest['files'][changed]['before_sha256']=='f083fe8b618f4b09dce1587b3c32bf47f92510948e728615ce989ef31a1757cf'
assert candidate_sha==manifest['files'][changed]['sha256']=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
assert {str(p.relative_to(candidate)).replace('\\','/') for p in candidate.rglob('*.py')}=={changed}
archive=json.loads((SOURCE/'v1/ARCHIVE_MANIFEST.json').read_text(encoding='utf-8'))
for path,sha in archive.items():assert hashlib.sha256((SOURCE/'v1'/path).read_bytes()).hexdigest()==sha,path
recorded=json.loads((HERE.parent/'parallel_platform/gui_startup_review/gui_bootstrap_01.json').read_text(encoding='utf-8'))['board_result']
path='/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json'
recorded_startup=json.loads(recorded['files'][path]['text']);pins=recorded_startup['component_sha256']
review_paths=(changed,'common/voice_enrollment.py','tools/provisional_voice.py','tools/binding_hub_runtime.py',
    'board/runtime/board_speaker_business.py','common/identity_links.py','common/binding_api.py')
assert all(manifest['baseline_files'][p]['sha256']==pins[p] for p in review_paths)
base_ast=ast.parse(before.decode());new_ast=ast.parse(after.decode());patched=copy.deepcopy(new_ast)
klass=next(n for n in patched.body if isinstance(n,ast.ClassDef) and n.name=='UnifiedBindingRouter')
route=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='route')
voice=next(n for n in ast.walk(route) if isinstance(n,ast.If) and ast.unparse(n.test)=="state == 'SAMPLING_VOICE'")
assert isinstance(voice.body[0],ast.ImportFrom) and voice.body[0].module=='tools.provisional_voice'
assert [a.name for a in voice.body[0].names]==['query_reply']
assert ast.unparse(voice.body[1])=="if query_reply(text, {'state': 'UNKNOWN'}) is not None:\n    return self.decision('ordinary', reason='IDENTITY_QUERY_DURING_VOICE_ENROLLMENT')"
voice.body=voice.body[2:]
assert ast.dump(patched,include_attributes=False)==ast.dump(base_ast,include_attributes=False)
current_startup=copy.deepcopy(recorded_startup)
current_startup['component_sha256']['config/board_avatar_gtk.json']='fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
encode=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
assert hashlib.sha256(encode(current_startup)).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
predicted=copy.deepcopy(current_startup);predicted['component_sha256'][changed]=candidate_sha
predicted_sha=hashlib.sha256(encode(predicted)).hexdigest()
assert predicted_sha=='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
assert len(predicted['component_sha256'])==380
assert [p for p in pins if current_startup['component_sha256'][p]!=predicted['component_sha256'][p]]==[changed]
sys.path.insert(0,str(baseline))
import common,tools
common.__path__=[str(baseline/'common')];tools.__path__=[str(candidate/'tools'),str(baseline/'tools')]
spec=importlib.util.spec_from_file_location('review_public_identity_fixtures_v2',SOURCE/'test_identity_query_isolation.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
buffer=io.StringIO()
result=unittest.TextTestRunner(verbosity=2,stream=buffer).run(unittest.defaultTestLoader.loadTestsFromModule(fixtures))
with (HERE/'INDEPENDENT_QUERY_TESTS_V2.log').open('x',encoding='utf-8') as stream:stream.write(buffer.getvalue())
assert result.wasSuccessful() and result.testsRun==15
from tools.provisional_voice import query_reply
extra=[]
for phrase in ('听声音我是谁','你认识我的声音吗'):
    meta,scene,registry,speaker,hub=fixtures.hub_fixture()
    before_stage=speaker.sessions[hub.router.actor(meta)]['stage']
    response=hub.route(meta,phrase,fixtures.PCM,visual=scene)
    row={'phrase':phrase,'original_query_predicate_accepts':query_reply(phrase,{'state':'UNKNOWN'}) is not None,
        'decision_reason':response['decision']['reason'],'speaker_turn_call_count':len(speaker.calls),
        'stage_before':before_stage,'stage_after':speaker.sessions[hub.router.actor(meta)]['stage'],
        'identity_resolver_call_count':registry.resolve_calls,'personal_memory_allowed':response['decision']['personal_memory_allowed']}
    assert row['decision_reason']=='EXPLICIT_IDENTITY_QUERY' and row['speaker_turn_call_count']==0
    assert row['stage_before']==row['stage_after']=='sample1' and row['identity_resolver_call_count']==1
    assert row['personal_memory_allowed'] is False
    extra.append(row)
xml=ET.fromstring((SOURCE/'ORIGINAL_REGRESSION_V2.xml').read_bytes())
suites=list(xml.iter('testsuite'))
original_regression={'tests':sum(int(s.attrib.get('tests',0)) for s in suites),
    'failures':sum(int(s.attrib.get('failures',0)) for s in suites),'errors':sum(int(s.attrib.get('errors',0)) for s in suites),
    'skipped':sum(int(s.attrib.get('skipped',0)) for s in suites),'execution':'candidate_owner_run_receipt_read_only_verified'}
assert original_regression['tests']==22 and original_regression['failures']==original_regression['errors']==original_regression['skipped']==0
assert hashlib.sha256((candidate/changed).read_bytes()).hexdigest()==candidate_sha
audit={'schema':'aura-independent-identity-query-review-v2-1','status':'PASS_NO_REMAINING_CODE_REVIEW_BLOCKERS',
    'candidate_sha256':candidate_sha,'baseline_sha256':hashlib.sha256(before).hexdigest(),
    'source_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'baseline_files_verified':len(manifest['baseline_files']),
    'v1_archive_files_verified':len(archive),'reviewed_dependency_pins':{p:pins[p] for p in review_paths},
    'single_changed_component':changed,'only_added_AST_nodes_are_pure_query_predicate_import_and_guard':True,
    'independent_provided_test_methods':result.testsRun,'independent_failures':len(result.failures),'independent_errors':len(result.errors),
    'v1_missing_queries_now_resolved_without_enrollment_samples':extra,'original_regression_receipt':original_regression,
    'current_startup_reconstructed_sha256':'3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591',
    'predicted_single_pin_startup_sha256':predicted_sha,'predicted_component_count':380,
    'candidate_or_production_modified':False,'board_accessed':False,'private_store_opened':False,'models_or_devices_accessed':False}
with (HERE/'INDEPENDENT_AUDIT_V2.json').open('x',encoding='utf-8') as stream:
    json.dump(audit,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({'status':audit['status'],'candidate_sha256':candidate_sha,
    'independent_test_methods':result.testsRun,'original_regression_receipt':original_regression,
    'resolved_v1_edges':extra,'predicted_startup_sha256':predicted_sha,'board_accessed':False},ensure_ascii=False))
