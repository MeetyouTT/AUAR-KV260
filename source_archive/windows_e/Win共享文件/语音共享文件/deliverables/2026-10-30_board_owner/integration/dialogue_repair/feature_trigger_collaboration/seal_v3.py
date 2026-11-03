"""Freeze the reviewed retry/cancellation fix without altering v1/v2 bytes."""
import ast
import difflib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from seal_v2 import digest,methods

HERE=Path(__file__).resolve().parent
VERSION=HERE/'candidate_v3'


def main():
    v2=HERE/'candidate_v2/SOURCE_MANIFEST.json'
    if digest(v2)['sha256']!='8366977e473ca226af8c714b13bdde00eaba1b37ae0a157d30042d319c99824f':
        raise ValueError('Frozen v2 manifest changed')
    previous=json.loads(v2.read_bytes())
    for row in previous['files'].values():
        if digest(Path(row['source']))['sha256']!=row['sha256']:
            raise ValueError('Frozen v2 source changed')
    for rel,row in previous['files'].items():
        if rel not in ('common/feature_intents.py','tools/speaker_device.py'):
            if digest(VERSION/'after'/rel)['sha256']!=row['sha256']:
                raise ValueError('An unrelated carried-forward v2 source changed')
    pins=json.loads((HERE.parent/'paraformer_small_validation/v16_evidence/source_mapping.json').read_bytes())
    files={};patch=[];delta=[]
    for path in sorted((VERSION/'after').rglob('*.py')):
        rel=path.relative_to(VERSION/'after').as_posix()
        ast.parse(path.read_bytes(),feature_version=(3,9))
        before=VERSION/'before'/rel
        if before.exists() and digest(before)['sha256']!=pins['component_pins'][rel]:
            raise ValueError('Before-source is not the actual v16 source')
        old=before.read_text(encoding='utf-8') if before.exists() else ''
        new=path.read_text(encoding='utf-8')
        files[rel]=dict(source=str(path),before_sha256=digest(before)['sha256'] if before.exists() else None,**digest(path))
        patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before/'+rel,tofile='after/'+rel))
        parent=HERE/'candidate_v2/after'/rel
        parent=parent if parent.exists() else before
        parent_text=parent.read_text(encoding='utf-8') if parent.exists() else ''
        delta.extend(difflib.unified_diff(parent_text.splitlines(True),new.splitlines(True),fromfile='v2/'+rel,tofile='v3/'+rel))
    if set(files)!=set(previous['files'])|{'board/runtime/board_speaker_business.py'}:
        raise ValueError('Unexpected v3 production source scope')
    invariants={}
    for rel,cls,allowed in (
        ('tools/speaker_device.py','SpeakerDevice',{'turn','_turn'}),
        ('board/runtime/board_speaker_business.py','BoardSpeakerBusiness',{'_run','_call','_clear_status_receipt','_cancel_actor','reset'}),
        ('board/runtime/board_business.py','BoardBusinessRuntime',set()),
    ):
        old=methods(VERSION/'before'/rel,cls);new=methods(VERSION/'after'/rel,cls)
        changed={name for name in set(old)|set(new) if old.get(name)!=new.get(name)}
        if changed!=allowed:raise ValueError('Unexpected method scope: '+cls)
        invariants[cls]=dict(changed_methods=sorted(changed),all_other_methods_ast_equal=True)
    suite=ET.parse(VERSION/'TESTS.xml').getroot().find('testsuite')
    if int(suite.attrib.get('failures',0))+int(suite.attrib.get('errors',0)):
        raise ValueError('v3 tests are not passing')
    tests=dict(level='code_or_fake_verified',tests=int(suite.attrib['tests']),failures=0,errors=0,
        scope='7new v3 cases +16v2 focused cases +16original BoardSpeakerBusiness cases; no hardware/models.',
        receipt=dict(path=str(VERSION/'TESTS.xml'),**digest(VERSION/'TESTS.xml')))
    manifest=dict(schema='aura.feature-trigger-source-candidate.v3',status='FROZEN_NOT_DEPLOYED',
        source_baseline_startup_sha256=pins['startup_sha256'],source_baseline_manifest_sha256=pins['source_manifest_sha256'],
        superseded_frozen_v2=dict(path=str(v2),**digest(v2)),files=files,invariant_checks=invariants,
        thresholds_models_identity_permissions_playback_drivers_changed=False,
        private_data_accessed=False,production_deployed=False)
    (VERSION/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (VERSION/'extra_source_map.json').write_text(json.dumps({k:v['source'] for k,v in files.items()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (VERSION/'review.patch').write_text(''.join(patch),encoding='utf-8')
    (VERSION/'review_from_v2.patch').write_text(''.join(delta),encoding='utf-8')
    command=['D:/py312/python.exe','-B','-X','utf8',str(HERE/'run_candidate_tests.py'),'--candidate-v3',
        str(HERE/'tests/test_feature_v3.py'),str(HERE/'tests/test_feature_v2.py'),
        str(HERE.parents[4]/'aura/tests/framework/test_board_speaker_business.py'),
        '-q','-p','no:cacheprovider','--import-mode=importlib','--basetemp='+str(HERE/'v3_test_work'),
        '--junitxml='+str(VERSION/'TESTS.xml')]
    handoff=dict(schema='aura.feature-trigger-handoff.v3',status='LOCAL_V3_FROZEN_NOT_DEPLOYED',
        latest_candidate='candidate_v3',do_not_integrate_v1=True,do_not_integrate_v2=True,
        source_manifest=dict(path=str(VERSION/'SOURCE_MANIFEST.json'),**digest(VERSION/'SOURCE_MANIFEST.json')),
        baseline_startup_sha256=pins['startup_sha256'],source_files=len(files),tests=tests,test_command=command,
        independent_cases_replayed=dict(tests=3,failures=0,original_source_or_assertions_changed=False,
            original_negative_evidence_preserved=True,receipt=dict(path=str(VERSION/'INDEPENDENT_REPLAY.json'),**digest(VERSION/'INDEPENDENT_REPLAY.json')),
            xml=dict(path=str(VERSION/'INDEPENDENT_REPLAY.xml'),**digest(VERSION/'INDEPENDENT_REPLAY.xml')),
            command=['D:/py312/python.exe','-B','-X','utf8',str(HERE/'replay_independent_edges_v3.py')]),
        changes=['Retain allv2 routing/status fixes, including actual paired route.',
            'Read-only status retries with identical complete meta still verify fingerprint then reevaluate TTL/speaker revision/actor.',
            'Original write-command replay stays idempotent; changed text/PCM fingerprint still rejected.',
            'Worker errors/cancellation clear only temporary metadata receipts; actual committed identity rows remain.',
            'Check current again when the completed future is adopted; queue receipt cleanup for caller-side late cancellation.',
            'Common verb-before-object status questions, including你有没有保存我的声纹, bypass active enrollment samples.'],
        proof=['Same-rid actual BoardSpeakerBusiness retry at61seconds and changed speaker revision => cannot determine.',
            'Original save same-rid retry does not enroll twice; fingerprint mismatch rejected.',
            'Before-commit failure =>0identities/0receipts; both after-commit cancel seams =>1identity/0receipts, never reported unsaved.',
            'Actual paired request, fullACK, four common status questions =>samples0/hashes0/identities0/grants0.'],
        actual_model_review=dict(path=str(HERE/'ROOT_REVIEW.json'),strict_pass=2,qualified=1,failed=1,
            function_calling_verified=False,production_feature_routing_was_bypassed=True),
        remaining=['Independent review and root integration still pending; production remainsv16/PAUSED.',
            'No actual camera/voice/human acceptance or physical playback test for this candidate.',
            'reasoning_dialogue/history_delete_preview remain absent; spatial/object/voice-auth limitations unchanged.'],
        rollback=['Root normal release restores7original before sources/pins and removes new helper binding after references restored.',
            'Never roll back/delete committed identities, private stores/preferences/models or replay old receipts.'],
        production_actions_by_feature_chat=[])
    (VERSION/'HANDOFF.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    index=HERE/'HANDOFF.json';archive=HERE/'HANDOFF_v2_frozen.json'
    if index.exists() and not archive.exists():archive.write_bytes(index.read_bytes())
    index.write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=handoff['status'],source_manifest=handoff['source_manifest'],tests=tests),ensure_ascii=False))


if __name__=='__main__':main()
