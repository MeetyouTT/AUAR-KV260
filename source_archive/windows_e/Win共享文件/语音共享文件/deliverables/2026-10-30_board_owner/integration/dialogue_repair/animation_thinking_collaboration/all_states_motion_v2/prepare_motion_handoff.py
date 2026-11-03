"""Bind the all-state motion candidate to saved v17 evidence; no device IO."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ANIMATION=HERE.parent
REPAIR=ANIMATION.parent
PROJECT=HERE.parents[5]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    evidence=REPAIR/'release_v17_candidate/v17_evidence'
    mapping_path=evidence/'source_mapping.json'
    mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
    pins=mapping['component_pins']
    if len(pins)!=379 or mapping['startup_sha256']!='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a':
        raise ValueError('Expected v17 saved production evidence')
    renderer={name:digest for name,digest in json.loads((ANIMATION/'paired_overlay/PAIRING_RECEIPT.json').read_text(encoding='utf-8'))['files'].items()}
    for relative,expected in renderer.items():
        source=ANIMATION/'paired_overlay/aura'/relative
        if sha(source)!=expected or pins[relative]!=expected:raise ValueError('Renderer base is not v17')
        destination=HERE/'before/aura'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists() and sha(destination)!=expected:raise ValueError('Frozen before changed')
        shutil.copyfile(source,destination)
    build=json.loads((ANIMATION/'native_build_result/native_build_receipt.json').read_text(encoding='utf-8'))
    if sha(HERE/'before/native/yuki_host.cpp')!=build['source_sha256'] or sha(HERE/'before/native/yuki_host.h')!=build['header_sha256']:
        raise ValueError('Motion ancestor does not match current native library provenance')
    base=dict(schema='aura.all-state-motion-baseline-v17.v2',root=mapping['root'],
        startup_sha256=mapping['startup_sha256'],source_manifest_sha256=mapping['source_manifest_sha256'],
        component_pins=len(pins),source_mapping_path=str(mapping_path),source_mapping_sha256=sha(mapping_path),
        renderer_pins=renderer,native_build_receipt_sha256=sha(ANIMATION/'native_build_result/native_build_receipt.json'),
        feature_v3_yuki_jobs_pin=pins['tools/yuki_jobs_candidate.py'],
        current_state_source='Saved v17 evidence; device owner must re-read before any test/publish',
        user_paused_preserved=True,private_data_read=False)
    save(HERE/'BASELINE_V17.json',base)
    model=PROJECT/'deliverables/2026-10-30_yuki_native_validation/native_integration/runtime_assets/model.runtime.json'
    if sha(model)!=pins['assets/yuki/model.runtime.json']:raise ValueError('Public character asset mismatch')
    metadata=json.loads(model.read_text(encoding='utf-8'))['metadata']
    names=('head_LR','head_UD','head_slant','body_LR','body_UD','body_slant')
    bounds=dict(zip(names,(3.6,1.6,1.9,.65,.5,.65)))
    loops=[]
    for timeline in metadata['timelineControl']:
        if not timeline['label'].endswith('通常待機'):continue
        ranges={}
        for variable in timeline['variableList']:
            if variable['label'] not in names:continue
            values=[frame['content']['value'] for frame in variable['frameList']
                    if isinstance(frame.get('content'),dict) and 'value' in frame['content']] or [0]
            low,high=min(values),max(values);limit=bounds[variable['label']]
            if low-limit < -30 or high+limit>30:raise ValueError('Additive motion exceeds authored safe range')
            ranges[variable['label']]=dict(authored_min=low,authored_max=high,added_bound=limit)
        if set(ranges)!=set(names):raise ValueError('Missing authored motion channel')
        loops.append(dict(label=timeline['label'],loop_end=timeline['loopEnd'],ranges=ranges))
    if len(loops)!=2:raise ValueError('Expected two existing idle poses')
    chains={key:[{k:row[k] for k in ('label','baseLayer','var_lr','var_ud','var_lrm','enabled') if k in row}
                 for row in metadata[key]] for key in ('hairControl','partsControl')}
    if len(chains['hairControl'])!=4 or len(chains['partsControl'])!=2:
        raise ValueError('Unexpected existing physical part groups')
    resource=dict(schema='aura.all-state-motion-resource-audit.v2',model_sha256=sha(model),
        head_body_parameters=list(names),authored_pose_ranges=loops,existing_physics=chains,
        motion_insert_point='Existing AuthorTickHandler before animation/geometry/physics step',
        model_or_texture_modified=False,physics_controller_parameters_modified=False,
        extra_draw_calls=0,extra_physics_steps=0,extra_timers=0,extra_processes=0,
        all_requested_states=['IDLE','LISTENING','THINKING','ANSWER','PAUSED','CANCELLED'],
        calm_style_shared_by_idle_and_listening=True)
    save(HERE/'RESOURCE_AUDIT.json',resource)
    rows={};patch=[]
    for path in sorted((HERE/'candidate').rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(HERE/'candidate').as_posix();before=HERE/'before'/relative
        rows[relative]=dict(before_sha256=sha(before) if before.exists() else None,
                           after_sha256=sha(path),bytes=path.stat().st_size)
        patch.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(keepends=True) if before.exists() else [],
            path.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
    (HERE/'changes.patch').write_text(''.join(patch),encoding='utf-8')
    for path in HERE.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    manifest=dict(schema='aura.all-state-motion-source-manifest.v2',
        status='FROZEN_NATIVE_BUILD_AND_DYNAMIC_PREVIEW_REQUIRED',base=base,files=rows,
        no_python_business_or_feature_route_code_changed=True,
        binary_control_and_stats_layout_unchanged=True,new_feature_bit=2,
        native_library_built=False,visual_preview_passed=False,physical_fps_acceptance_passed=False,
        patch_sha256=sha(HERE/'changes.patch'))
    save(HERE/'SOURCE_MANIFEST.json',manifest)
    visual=ANIMATION/'ROOT_VISUAL_REVIEW.json'
    deployment=dict(schema='aura.eye-gating-v17-deployed.v1',
        status='DEPLOYED_V17_PUBLIC_CHARACTER_VISUAL_PASS_HUMAN_LIPSYNC_UNVERIFIED',
        startup_sha256=base['startup_sha256'],source_manifest_sha256=base['source_manifest_sha256'],
        renderer_pins=renderer,visual_review_sha256=sha(visual),
        evidence_source='Verified saved v17 source mapping plus main owner visual review',
        user_paused_preserved=True,new_all_state_motion_included=False,
        physical_lipsync_acceptance_passed=False,physical_fps_acceptance_passed=False)
    save(ANIMATION/'EYE_GATING_DEPLOYED_V17.json',deployment)
    names=['candidate/native/yuki_host.cpp','candidate/native/yuki_host.h','candidate/native/gentle_motion.hpp',
           'tests/native_eye_gate.cpp','tests/native_all_states_motion.cpp','build_native_isolated.py',
           'NATIVE_BASELINE.json','SOURCE_MANIFEST.json','RESOURCE_AUDIT.json']
    archive=HERE/'native_motion_source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for name in names:output.write(HERE/name,name)
    handoff=dict(schema='aura.all-state-motion-handoff.v2',status=manifest['status'],
        base_startup_sha256=base['startup_sha256'],base_source_manifest_sha256=base['source_manifest_sha256'],
        source_manifest_sha256=sha(HERE/'SOURCE_MANIFEST.json'),resource_audit_sha256=sha(HERE/'RESOURCE_AUDIT.json'),
        files=rows,archive=dict(path=archive.name,sha256=sha(archive),bytes=archive.stat().st_size),
        existing_eye_gate_unchanged=True,features_routes_unchanged=True,
        mandatory_native_tests=['Existing eye/mouth/owner/TTL regression',
            '12000 real C++ policy author ticks with rapid mood/voice changes and bounded deltas',
            '960 real native frames across idle/listening/thinking/answer/pause/cancel and both poses',
            'Six head/body channels vary in every state; multiple existing hair/parts outputs move; no extra author tick'],
        native_build_command='Same root-owned build_native_isolated.py CLI; package is new and must not overwrite the eye-gating stage',
        paired_overlay_script='seal_motion_overlay.py',
        preview_required='Single-owner pure-character sequences at two or more times in each state, not a single still; verify non-rigid head/torso/hair/parts lag',
        device_actions_this_window=False,production_modified=False,model_inference=False,
        native_test_executed=False,visual_preview_passed=False,
        baseline_v17_routes_must_survive_merge=True,do_not_restore_v16_startup=True,
        new_ui_config_binding='config/board_avatar_gtk.json character_pair.selection_sha256 and its startup component pin after reseal',
        rollback='Revert only new native lib/pair selection and formal pair constant against current production; keep feature v3 and user PAUSED')
    save(HERE/'HANDOFF.json',handoff)
    print(json.dumps(dict(status=handoff['status'],native_source_files=len(rows),archive=handoff['archive'])))


if __name__=='__main__':main()
