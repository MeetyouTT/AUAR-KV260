"""Freeze a display-only preview package and paired handoff; no device access."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    frozen=json.loads((HERE/'HANDOFF.json').read_text(encoding='utf-8'))
    manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for name,expected in frozen['helper_pins'].items():
        if sha(HERE/name)!=expected:raise ValueError('Frozen helper changed: '+name)
    for name,row in manifest['files'].items():
        if sha(HERE/'candidate'/name)!=row['after_sha256']:raise ValueError('Frozen source changed: '+name)
    pairing_path=HERE/'paired_overlay/PAIRING_RECEIPT.json'
    pairing=json.loads(pairing_path.read_text(encoding='utf-8'))
    tests=json.loads((HERE/'PAIRED_TEST_RESULTS.json').read_text(encoding='utf-8'))
    if (tests.get('successful') is not True or tests.get('tests_run')!=29 or
        tests['pairing_receipt_sha256']!=sha(pairing_path) or tests['files']!=pairing['files']):
        raise ValueError('Matching paired tests required')
    for relative,expected in pairing['files'].items():
        if sha(HERE/'paired_overlay/aura'/relative)!=expected:raise ValueError('Paired file changed: '+relative)
    old_selection=json.loads((HERE/'before/aura/config/yuki_pair.formal.json').read_text(encoding='utf-8'))
    new_selection=json.loads((HERE/'paired_overlay/aura/config/yuki_pair.formal.json').read_text(encoding='utf-8'))
    changed={name for name in old_selection['runtime_pins']
             if old_selection['runtime_pins'][name]!=new_selection['runtime_pins'][name]}
    if changed!={'tools/native_yuki.py','tools/libaura_yuki.so'}:
        raise ValueError('Unexpected inner pair pin scope')
    if 'tools/yuki_jobs_candidate.py' in new_selection['runtime_pins']:
        raise ValueError('Unexpected feature route pin in renderer pair')
    preview=HERE/'preview_public_states.py'
    ast.parse(preview.read_text(encoding='utf-8'))
    public_pins={name:digest for name,digest in new_selection['runtime_pins'].items()
                 if name.startswith('assets/yuki/') or name=='tools/egl_window.py'}
    spec=dict(schema='aura.animation-thinking-preview-spec.v1',script_sha256=sha(preview),
        overlay_pins=pairing['files'],selection_sha256=pairing['selection_sha256'],
        public_runtime_pins=public_pins,render_size=[423,516],target_fps=16,
        input_scope='Public simulated states and numerical envelope; no audio engine or PCM',
        capture_scope='Native renderer.capture 423x516 character framebuffer; no desktop/camera/UI screenshots',
        owner_precondition='Coordinator normal-close production; MainPID must be 0; one preview process',
        automatic_restore_or_publish=False)
    save('PREVIEW_SPEC.json',spec)
    source=HERE/'runtime_v16/tools/realtime_audio.py'
    tree=ast.parse(source.read_text(encoding='utf-8'));lines=source.read_text(encoding='utf-8').splitlines()
    owner=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='SelectedAudioOutput')
    read=next(node for node in owner.body if isinstance(node,ast.FunctionDef) and node.name=='read')
    facade=HERE/'runtime_v16/tools/gstreamer_audio.py'
    facade_tree=ast.parse(facade.read_text(encoding='utf-8'))
    facade_owner=next(node for node in facade_tree.body if isinstance(node,ast.ClassDef) and node.name=='GStreamerAudioOutput')
    if any(isinstance(node,ast.FunctionDef) and node.name=='read' for node in facade_owner.body):
        raise ValueError('GStreamer facade overrides cached read; re-audit required')
    note=dict(schema='aura.animation-thinking-output-read-audit.v1',
        source='Pinned v16 Python source inspection; no process/IPC benchmark',
        selected_audio_output_sha256=sha(source),read_line=read.lineno,
        read_body='\n'.join(lines[read.lineno-1:read.end_lineno]),
        gstreamer_audio_sha256=sha(facade),gstreamer_facade_overrides_read=False,
        conclusion='Additional output.read copies the in-process cached snapshot under its lock; it does not send a worker command, read a pipe, open a socket or invoke a model',
        caveat='One additional lock/dict copy in the display frame path; exact board CPU cost not benchmarked',
        frozen_candidate_modified=False)
    save('OUTPUT_READ_AUDIT.json',note)
    after={name:dict(before_sha256=sha(HERE/'before/aura'/name),after_sha256=digest)
           for name,digest in pairing['files'].items()}
    save('PAIRED_OVERLAY_SOURCE_MANIFEST.json',dict(schema='aura.animation-thinking-paired-source-manifest.v1',
        files=after,required_startup_change=pairing['required_startup_change'],
        actual_binding_target='GUI config/board_avatar_gtk.json: character_pair.selection_sha256; startup binds the GUI config component SHA',
        changed_inner_pair_pins=sorted(changed),feature_yuki_jobs_pinned=False,
        final_startup_component_manifest_must_be_recomputed=True,production_modified=False))
    names=['preview_public_states.py','PREVIEW_SPEC.json','PREVIEW_PLAN.txt',
           'paired_overlay/PAIRING_RECEIPT.json','PAIRED_TEST_RESULTS.json']
    names+=['paired_overlay/aura/'+name for name in pairing['files']]
    archive=HERE/'public_preview_source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for name in names:output.write(HERE/name,name)
    native=json.loads((HERE/'native_build_result/native_build_receipt.json').read_text(encoding='utf-8'))
    handoff=dict(schema='aura.animation-thinking-paired-handoff.v1',
        status='PAIRED_VERIFIED_NATIVE_CPU_PASS_PUBLIC_PREVIEW_READY_NOT_DEPLOYED',
        pairing_receipt_sha256=sha(pairing_path),paired_test_results_sha256=sha(HERE/'PAIRED_TEST_RESULTS.json'),
        paired_overlay_source_manifest_sha256=sha(HERE/'PAIRED_OVERLAY_SOURCE_MANIFEST.json'),
        preview_spec_sha256=sha(HERE/'PREVIEW_SPEC.json'),preview_script_sha256=sha(preview),
        preview_archive=dict(path=archive.name,sha256=sha(archive),bytes=archive.stat().st_size),
        preview_plan_sha256=sha(HERE/'PREVIEW_PLAN.txt'),output_read_audit_sha256=sha(HERE/'OUTPUT_READ_AUDIT.json'),
        files=pairing['files'],selection_sha256=pairing['selection_sha256'],
        required_startup_change=pairing['required_startup_change'],
        actual_binding_target='GUI config/board_avatar_gtk.json: character_pair.selection_sha256; recompute its startup component pin; do not add an unknown startup field',
        native_build_receipt_sha256=sha(HERE/'native_build_result/native_build_receipt.json'),
        native_cpu_test=native['native_policy_test'],local_paired_tests=29,
        frozen_candidate_and_helpers_unchanged=True,device_actions_this_window=False,
        private_data_read_or_exported=False,production_modified=False,
        preview_executed=False,visual_preview_passed=False,physical_fps_acceptance_passed=False,
        feature_yuki_jobs_candidate_in_inner_pair_pins=False,
        integration_note='Renderer inner pair pins do not cover feature routes; main owner must rebuild all final startup component hashes and source manifest after merging feature v3',
        next_owner_actions=['Review preview source/spec and numeric grading',
            'Normal-close production while retaining PAUSED and owned restore guard',
            'Run only this display preview with provided DISPLAY/XAUTHORITY and an owned bounded lifetime',
            'Inspect pure character captures; preserve metadata-only report',
            'Close preview completely, then restore current production or publish a reviewed combined revision'])
    save('PAIRED_HANDOFF.json',handoff)
    print(json.dumps(dict(status=handoff['status'],selection_sha256=handoff['selection_sha256'],
        pairing_receipt_sha256=sha(pairing_path),preview_archive=handoff['preview_archive'])))


if __name__=='__main__':
    main()
