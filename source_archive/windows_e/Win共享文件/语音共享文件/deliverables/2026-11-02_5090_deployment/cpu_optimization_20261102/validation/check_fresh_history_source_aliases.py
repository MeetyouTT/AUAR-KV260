"""Three isolated public-metadata alias probes, not the 16-test suite or CLI."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
CAMERA=HERE.parent/'camera'
SOURCE=CAMERA/'validate_fresh_final_history_readonly.py'
EXPECTED='e92d8b0c461ff060d2e6d5e0aceef81c13ad1580cc3f66ad118b27c805b9f102'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
spec=importlib.util.spec_from_file_location('fresh_alias_public_fixture',CAMERA/'test_fresh_final_history_readonly.py')
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)
candidate=fixture_module.candidate
results=[]
for mode in ('baseline','same_sha_sealed_copy','reformatted_same_owner_final','checkpoint_envelope'):
    snap,expected,intent,result,document=fixture_module.fixture()
    original_legacy=candidate.LEGACY_SHA
    candidate.LEGACY_SHA=expected['history']['legacy_pin']['sha256']
    try:
        source_pin=None
        if mode!='baseline':
            proof=snap.pinned(expected['history']['provenance_pin'])
            if mode=='same_sha_sealed_copy':
                source_pin=snap.put('/synthetic/sealed-final-copy.json',document)
                pointer='/previous_kernel_history'
            elif mode=='reformatted_same_owner_final':
                source_pin=snap.put('/synthetic/reformatted-final-copy.json',document,(json.dumps(document,indent=2)+'\n').encode())
                pointer='/previous_kernel_history'
            else:
                source_pin=snap.put('/synthetic/metadata-envelope.json',{'schema':'public-seal-envelope-1','checkpoint':copy.deepcopy(document)})
                pointer='/checkpoint/previous_kernel_history'
            proof['source_bindings']['head']={'pin':source_pin,'pointer':pointer}
            expected['history']['provenance_pin']=snap.put('/synthetic/prestop-history.json',proof)
        accepted=False;reason=None
        try:candidate.validate_inputs(expected,snap);accepted=True
        except (ValueError,KeyError,TypeError) as exc:reason=type(exc).__name__+': '+str(exc)
        results.append({'case':mode,'accepted':accepted,'rejection':reason,
            'same_sha_as_pending_final':source_pin['sha256']==expected['checkpoint_pin']['sha256'] if source_pin else None,
            'source_is_pending_final_document_or_envelope':mode!='baseline',
            'only_source_head_reference_changed':mode!='baseline'})
    finally:candidate.LEGACY_SHA=original_legacy
assert results[0]['accepted'] is True
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
report={'candidate_sha256':EXPECTED,'results':results,
    'unexpected_alias_acceptances':sum(row['accepted'] for row in results[1:]),
    'scope':'Existing public in-memory fixture; existing synthetic legacy-pin substitution only. No CLI/original_modules/guard executed; no board, proc, marker or service IO.',
    'malicious_root_forgery_claimed':False,'candidate_modified':False}
with (HERE/'FRESH_HISTORY_ALIAS_NEGATIVES.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
