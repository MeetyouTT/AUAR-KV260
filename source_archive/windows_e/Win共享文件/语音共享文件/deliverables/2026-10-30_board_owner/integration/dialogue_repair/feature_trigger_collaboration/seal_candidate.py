"""Freeze source-only candidate and evidence metadata; never publishes it."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent


def digest(path):
    raw=path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def units(path,kind,name=None):
    root=ast.parse(path.read_bytes())
    if name:
        root=next(n for n in root.body if isinstance(n,ast.ClassDef) and n.name==name)
    result={}
    for node in root.body:
        if isinstance(node,kind):
            key=getattr(node,'name',None)
            if key is None:
                targets=getattr(node,'targets',[])
                key=','.join(ast.dump(t) for t in targets)
            result[key]=ast.dump(node,include_attributes=False)
    return result


def main():
    mapping=HERE.parent/'paraformer_small_validation/v16_evidence/source_mapping.json'
    receipt=json.loads(mapping.read_bytes())
    source_verification=json.loads((HERE/'V16_SOURCE_VERIFICATION.json').read_bytes())
    baseline=json.loads((HERE/'candidate/SOURCE_BASELINE.json').read_bytes())
    rows={};patch=[]
    for path in sorted((HERE/'candidate/after').rglob('*.py')):
        rel=path.relative_to(HERE/'candidate/after').as_posix()
        ast.parse(path.read_bytes(),feature_version=(3,9))
        before=HERE/'candidate/before'/rel
        before_text=''
        if before.exists():
            info=digest(before)
            if info['sha256']!=receipt['component_pins'][rel] or info['sha256']!=baseline['files'][rel]['sha256']:
                raise ValueError('Before-source differs from verified v16: '+rel)
            before_text=before.read_text(encoding='utf-8')
        elif rel in receipt['component_pins']:
            raise ValueError('A new source overwrites an existing component')
        rows[rel]=dict(source=str(path),before_sha256=digest(before)['sha256'] if before.exists() else None,**digest(path))
        patch.extend(difflib.unified_diff(before_text.splitlines(True),path.read_text(encoding='utf-8').splitlines(True),
                                        fromfile='before/'+rel,tofile='after/'+rel))
    expected={'board/runtime/audio/board_dialogue_jobs.py','tools/yuki_jobs_candidate.py',
              'board/runtime/visual_policy.py','tools/speaker_device.py',
              'common/voice_enrollment.py','common/feature_intents.py'}
    if set(rows)!=expected:
        raise ValueError('Unexpected production source scope')
    invariant_checks={}
    for rel,cls,allowed in (
        ('board/runtime/audio/board_dialogue_jobs.py','BoardDialogueJobs',{'_route'}),
        ('tools/speaker_device.py','SpeakerDevice',{'_turn'}),
    ):
        before=units(HERE/'candidate/before'/rel,ast.FunctionDef,cls)
        after=units(HERE/'candidate/after'/rel,ast.FunctionDef,cls)
        changed={name for name in set(before)|set(after) if before.get(name)!=after.get(name)}
        if changed!=allowed:
            raise ValueError('Protected methods changed: '+rel)
        invariant_checks[rel]=dict(changed_methods=sorted(changed),all_other_methods_ast_equal=True)
    before=units(HERE/'candidate/before/tools/yuki_jobs_candidate.py',ast.FunctionDef)
    after=units(HERE/'candidate/after/tools/yuki_jobs_candidate.py',ast.FunctionDef)
    if {name for name in before if before[name]!=after[name]}!={'_route'}:
        raise ValueError('Paired admission guard changed')
    invariant_checks['tools/yuki_jobs_candidate.py']=dict(changed_methods=['_route'],admission_guard_ast_equal=True)
    before=units(HERE/'candidate/before/common/voice_enrollment.py',ast.FunctionDef)
    after=units(HERE/'candidate/after/common/voice_enrollment.py',ast.FunctionDef)
    if before!=after:
        raise ValueError('Enrollment parser/FSM functions changed')
    invariant_checks['common/voice_enrollment.py']=dict(all_functions_ast_equal=True,
        change='Only full direct read-only query grammar extended; no enrollment/confirmation/valid-name change')
    (HERE/'candidate/review.patch').write_text(''.join(patch),encoding='utf-8')
    (HERE/'candidate/extra_source_map.json').write_text(json.dumps({k:v['source'] for k,v in rows.items()},
        ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest=dict(schema='aura.feature-trigger-source-candidate.v1',status='FROZEN_NOT_DEPLOYED',
        baseline_startup_sha256=receipt['startup_sha256'],baseline_manifest_sha256=receipt['source_manifest_sha256'],
        source_mapping=digest(mapping),files=rows,invariant_checks=invariant_checks,
        production_config_changed=False,private_data_accessed=False,model_or_threshold_changes=False,
        crucial_binding='Formal factory binds tools/yuki_jobs_candidate._route; both bound/core routes included.')
    (HERE/'candidate/SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    suite=ET.parse(HERE/'TESTS.xml').getroot().find('testsuite')
    if int(suite.attrib.get('failures',0))+int(suite.attrib.get('errors',0)):
        raise ValueError('Final test receipt is not passing')
    evidence={name:dict(path=str(HERE/name),**digest(HERE/name)) for name in (
        'TESTS.xml','ROUTE_AUDIT_BASELINE_PAIRED.json','ROUTE_AUDIT_CANDIDATE_PAIRED.json',
        'V16_SOURCE_VERIFICATION.json','CURRENT_TEST_ADAPTATIONS.json','PUBLIC_PROBE_PIN.json',
        'candidate/SOURCE_MANIFEST.json','candidate/extra_source_map.json','candidate/review.patch',
        'public_board_probe_v2/STAGE_BUNDLE.json','public_board_probe_v2/TESTS.xml',
        'TEST_MATRIX.json','功能触发核查短报告.txt','真人联合验收脚本.txt')}
    handoff=dict(schema='aura.feature-trigger-handoff.v1',status='FROZEN_LOCAL_CANDIDATE_AWAITING_ROOT_INTEGRATION',
        release_owner_chat='01a18bcd-1167-71a0-ba0b-d809148d39d9',
        source_baseline=dict(startup_sha256=receipt['startup_sha256'],manifest_sha256=receipt['source_manifest_sha256'],
                             local_runtime_sources=len(source_verification['files'])),
        verification=dict(level='code_or_fake_verified',tests=int(suite.attrib['tests']),failures=0,errors=0,
                          deselected_historical_tests=3,physical_feature_acceptance=False,
                          tests_exclusion_reason=['Two retired Windows voice-business HTTP tests require removed service/config.',
                              'Old Windows writer-lock test assumes no bootstrap receipt; new test verifies both mandatory bootstrap and POSIX lock.'],
                          fixture_adaptations='Only retired character names replaced by selected current name; assertions unchanged.'),
        actual_architecture='Natural-language request -> board parser/router -> controlled local tool/FSM -> sourced direct reply/TTS. No LLM-generated tool-call protocol.',
        model_visibility=dict(current_visual='No image/object/spatial evidence sent to27B; direct count reply is local.',
                              identity='No biometric templates or grants; original local identity receipts only.',
                              ordinary_chat='Original978B device policy; explicit board-authorized text history/context only.'),
        candidate_scope=sorted(rows),evidence=evidence,
        root_next_steps=['Fresh verify all5 replaced source SHAs against current release, plus new helper absent or matching.',
                         'Review exact6-file patch including the INSTANCE-BOUND yuki route; integrate only through normal root release path.',
                         'Keep current PAUSED/mic=false, other model owners/parameters, camera/identity pins and real stores.',
                         'Run root-owned BOARD-ONLY public_board_probe_v2 by STAGE_BUNDLE.json in an exclusive slot; keep original Windows peer-denied evidence and record manual grounding review separately.',
                         'Then coordinate actual fresh camera count/unknown identity/status read-only checks; human enrollment/voice accuracy stays pending.'],
        rollback=['Restore exactly the5 before-source bytes and previous startup/source pins through root normal release.',
                  'Remove new helper component binding only after restoring its references; no private DB/preferences/clock anchor/model rollback.',
                  'If production has advanced, first rebase/verify SHAs; never apply this v16 full source over a newer change.'],
        remaining_gaps=['No registered reasoning_dialogue or history_delete_preview handler in the current factory.',
                        'No supported spatial/object/color visual result; person count is not presence identity or arbitrary scene understanding.',
                        'Voice thresholds still uncalibrated; no automatic profile grants or speaker-face authentication.',
                        'Human camera/reentry/voice accuracy, real audio playback and physical16fps not accepted by these tests.'],
        production_actions_by_feature_chat=[],weights_in_shared_tree_created=False)
    (HERE/'HANDOFF.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=handoff['status'],production_sources=len(rows),tests=handoff['verification'],
                         source_manifest=digest(HERE/'candidate/SOURCE_MANIFEST.json')),ensure_ascii=False))


if __name__=='__main__':
    main()
