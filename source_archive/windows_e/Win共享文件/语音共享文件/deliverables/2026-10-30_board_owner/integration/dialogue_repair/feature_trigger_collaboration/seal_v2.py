"""Freeze corrected local candidate_v2; preserve all frozen Version1 sources."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
VERSION=HERE/'candidate_v2'


def digest(path):
    raw=path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def methods(path,name):
    root=ast.parse(path.read_bytes())
    cls=next(n for n in root.body if isinstance(n,ast.ClassDef) and n.name==name)
    return {n.name:ast.dump(n,include_attributes=False) for n in cls.body if isinstance(n,ast.FunctionDef)}


def main():
    mapping=HERE.parent/'paraformer_small_validation/v16_evidence/source_mapping.json'
    receipt=json.loads(mapping.read_bytes())
    v1_path=HERE/'candidate/SOURCE_MANIFEST.json'
    if digest(v1_path)['sha256']!='c014eab845f0f577d31c2b0fa724ec44c5596de3993f16d2a0f459d5a89967be':
        raise ValueError('Original frozen Version1 manifest changed')
    v1=json.loads(v1_path.read_bytes())
    for row in v1['files'].values():
        if digest(Path(row['source']))['sha256']!=row['sha256']:
            raise ValueError('Original frozen Version1 source changed')
    rows={};patch=[]
    for path in sorted((VERSION/'after').rglob('*.py')):
        rel=path.relative_to(VERSION/'after').as_posix()
        ast.parse(path.read_bytes(),feature_version=(3,9))
        before=VERSION/'before'/rel
        old=''
        if before.exists():
            if digest(before)['sha256']!=receipt['component_pins'][rel]:
                raise ValueError('Version2 before-source differs from v16')
            old=before.read_text(encoding='utf-8')
        rows[rel]=dict(source=str(path),before_sha256=digest(before)['sha256'] if before.exists() else None,**digest(path))
        patch.extend(difflib.unified_diff(old.splitlines(True),path.read_text(encoding='utf-8').splitlines(True),
                     fromfile='before/'+rel,tofile='after/'+rel))
    if set(rows)!=set(v1['files'])|{'board/runtime/board_business.py'}:
        raise ValueError('Unexpected Version2 source scope')
    invariant={}
    for rel,name,allowed in (
        ('board/runtime/audio/board_dialogue_jobs.py','BoardDialogueJobs',{'_route'}),
        ('tools/speaker_device.py','SpeakerDevice',{'_turn'}),
        ('board/runtime/board_business.py','LocalIdentityReplies',{'__call__'}),
        ('board/runtime/board_business.py','BoardBusinessRuntime',set()),
    ):
        old=methods(VERSION/'before'/rel,name);new=methods(VERSION/'after'/rel,name)
        changed={key for key in set(old)|set(new) if old.get(key)!=new.get(key)}
        if changed!=allowed:
            raise ValueError('Protected method scope changed: '+name)
        invariant[rel+':'+name]=dict(changed_methods=sorted(changed),all_other_methods_ast_equal=True)
    tests={}
    for name in ('REGRESSION_TESTS.xml','FOCUSED_TESTS.xml'):
        suite=ET.parse(VERSION/name).getroot().find('testsuite')
        if int(suite.attrib.get('errors',0))+int(suite.attrib.get('failures',0)):
            raise ValueError('Version2 verification failed')
        tests[name]=dict(tests=int(suite.attrib['tests']),failures=0,errors=0,**digest(VERSION/name))
    manifest=dict(schema='aura.feature-trigger-source-candidate.v2',status='FROZEN_NOT_DEPLOYED',
        supersedes='Version1 has a known save-status wording regression; do not integrate Version1.',
        v1_original_preserved=digest(v1_path),baseline_startup_sha256=receipt['startup_sha256'],
        baseline_manifest_sha256=receipt['source_manifest_sha256'],files=rows,invariant_checks=invariant,
        source_scope='7files:6original targets plus the actual LocalIdentityReplies read-only status bypass.',
        model_prompt_or_threshold_or_playback_or_driver_changes=False,private_data_accessed=False)
    (VERSION/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (VERSION/'extra_source_map.json').write_text(json.dumps({rel:row['source'] for rel,row in rows.items()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (VERSION/'review.patch').write_text(''.join(patch),encoding='utf-8')
    handoff=dict(schema='aura.feature-trigger-handoff.v2',status='LOCAL_V2_FROZEN_NOT_DEPLOYED',
        latest_candidate='candidate_v2',source_manifest=dict(path=str(VERSION/'SOURCE_MANIFEST.json'),**digest(VERSION/'SOURCE_MANIFEST.json')),
        do_not_integrate_v1=True,v1_reason='Known Q2 save-status wording regresses to ordinary dialogue; frozen bytes preserved.',
        baseline_startup_sha256=receipt['startup_sha256'],source_files=7,
        tests=tests,verification_level='code_or_fake_verified',physical_acceptance=False,
        regression_command=['D:/py312/python.exe','-B','-X','utf8',str(HERE/'run_candidate_tests.py'),'--candidate-v2'],
        focused_command=['D:/py312/python.exe','-B','-X','utf8',str(HERE/'run_candidate_tests.py'),'--candidate-v2',
            str(HERE/'tests/test_feature_v2.py'),'-q','-p','no:cacheprovider','--import-mode=importlib',
            '--basetemp='+str(HERE/'v2_test_work'),'--junitxml='+str(VERSION/'FOCUSED_TESTS.xml')],
        actual_root_model_review=dict(path=str(HERE/'ROOT_REVIEW.json'),**digest(HERE/'ROOT_REVIEW.json'),
                                     strict_pass=2,qualified=1,failed=1,function_calling_verified=False),
        three_version_paired_route_comparison={name:dict(path=str(HERE/name),**digest(HERE/name)) for name in
            ('PAIRED_ROUTE_BASELINE.json','PAIRED_ROUTE_V1.json','PAIRED_ROUTE_V2.json')},
        changes=['Retain Version1 functionality fixes and the actual instance-bound paired route.',
                 'Save-success questions route to a controlled read-only status result; no ordinary27B FSM guesses.',
                 'Status questions bypass unified enrollment/binding and cannot become a captured sample or confirmation.',
                 'No receipt => cannot determine saved/unsaved; no invented settings workflow.',
                 'Positive save status uses original DB commit plus exact new revision/identity presence; same actor/generation and60s TTL only.',
                 'Receipt is private process-local metadata, never a biometric authentication/grant and never reconstructed from model/spoken text.'],
        root_next_steps=['Do not integrate original Version1; its immutable sources/evidence are retained for audit.',
                         'Fresh compare every Version2 before SHA against current production; rebase if any file has advanced.',
                         'Review7-file patch and coordinate a new root-owned integration/physical slot when available.',
                         'Keep user PAUSED; no feature-chat production/service/private-store action is authorized by this handoff.'],
        remaining=['Real camera/voice/human accuracy and final controlled status path on board remain pending.',
                   'reasoning_dialogue/history_delete_preview handlers remain absent and fail closed.',
                   'No arbitrary visual understanding or spatial counts; no calibrated voice authentication.'],
        rollback=['Through root normal release restore the6 Version2 before-source files/pins; unbind new helper after removing references.',
                  'Never restore private databases/preferences/models/old receipts or replay old identity data.'],
        production_actions_by_feature_chat=[])
    (VERSION/'HANDOFF.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Archive the previous index, then make the main entry unambiguously point
    # to Version2. The frozen Version1 source manifest/before/after stay intact.
    old_index=HERE/'HANDOFF.json'
    archive=HERE/'HANDOFF_v1_frozen.json'
    if old_index.exists() and not archive.exists():archive.write_bytes(old_index.read_bytes())
    old_index.write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=handoff['status'],source_manifest=handoff['source_manifest'],tests=tests),ensure_ascii=False))


if __name__=='__main__':main()
