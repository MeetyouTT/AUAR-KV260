"""Verify final v24 metadata/pins; carry unchanged v23 facial evidence."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
MOTION=HERE.parent
ANIM=MOTION.parent
REPAIR=ANIM.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence=REPAIR/'release_v24_memory_followup_candidate/memory_followup_evidence'
    expected={'spec.json':'9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1',
        'source_mapping.json':'6fb9899571078207b7460ae71d6da52ccd211c150b7d39f54f4003e672ec21c9'}
    for name,digest in expected.items():
        if sha(evidence/name)!=digest:raise ValueError('Current v24 evidence differs: '+name)
    spec=json.loads((evidence/'spec.json').read_text(encoding='utf-8'))
    mapping=json.loads((evidence/'source_mapping.json').read_text(encoding='utf-8'))
    if (spec['startup_sha256']!=mapping['startup_sha256']
            or spec['source_manifest_sha256']!=mapping['source_manifest_sha256']):
        raise ValueError('v24 identity mismatch')
    old=json.loads((REPAIR/'release_v23_memory_summary_candidate/memory_summary_evidence/source_mapping.json').read_text(encoding='utf-8'))
    prior=json.loads((MOTION/'v23_binding/V23_GATE_RESULTS.json').read_text(encoding='utf-8'))
    for name,digest in prior['loaded_dependency_pins'].items():
        if mapping['component_pins'].get(name)!=digest:raise ValueError('Gate retest required: '+name)
    for name,digest in prior['pair_pins'].items():
        if mapping['component_pins'].get(name)!=digest:raise ValueError('Pair changed: '+name)
    render_names=('tools/board_avatar_gtk.py','tools/board_avatar_worker.py','tools/formal_native_yuki.py',
        'tools/native_yuki.py','tools/egl_window.py','tools/libaura_yuki.so','config/yuki_pair.formal.json')
    render={name:mapping['component_pins'][name] for name in render_names}
    if any(digest!=old['component_pins'].get(name) for name,digest in render.items()):
        raise ValueError('Rendering source changed')
    changes={name:dict(before=old['component_pins'].get(name),after=digest)
        for name,digest in mapping['component_pins'].items() if old['component_pins'].get(name)!=digest}
    if set(changes)!={'board/runtime/board_memory_policy.py'}:raise ValueError('Unexpected v24 delta')
    package=json.loads((MOTION/'PACKAGE_RECEIPT.json').read_text(encoding='utf-8'))
    if sha(MOTION/package['archive'])!=package['sha256']:raise ValueError('Frozen candidate package changed')
    report=dict(schema='aura.minimal-motion-v24-metadata-binding.v1',status='V24_PINS_VERIFIED_V23_TEST_EVIDENCE_CARRIED_NO_RETEST',
        startup_sha256=mapping['startup_sha256'],source_manifest_sha256=mapping['source_manifest_sha256'],
        configuration_sha256=spec['configuration_sha256'],evidence_sha256=expected,
        rendering_pins=render,unchanged_gate_dependency_count=len(prior['loaded_dependency_pins']),
        carried_test_version='v23',carried_gate_test_count=prior['tests_run'],tests_rerun_this_update=0,
        carried_gate_results_sha256=sha(MOTION/'v23_binding/V23_GATE_RESULTS.json'),
        protected_changed_sources_not_modified=changes,frozen_source_package_sha256=package['sha256'],
        ui_page_required='main',raw_visible_required=dict(present=True,json_type='boolean',value=True),
        frame_scheduling_required=dict(present=True,json_type='boolean',value=True),
        visible_proves_physical_display_awake=False,pure_preview_is_not_business_main=True,
        v25_unpublished_must_not_be_used_as_baseline=True,native_candidate_executed=False,
        production_modified=False,device_actions=False,model_or_compile_service_started=False)
    (HERE/'V24_METADATA_BINDING.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    handoff=dict(schema='aura.minimal-motion-v24-handoff.v1',status=report['status'],
        startup_sha256=report['startup_sha256'],source_manifest_sha256=report['source_manifest_sha256'],
        direction='Two mild head channels, existing hair/parts physics and real-audible facial gates',
        candidate_source_package_sha256=package['sha256'],pin_binding='V24_METADATA_BINDING.json',
        measurement_addendum='MEASUREMENT_BOUNDARY.txt',gate_tests_carried_from_v23=25,
        tests_rerun_this_update=0,new_memory_policy_protected=True,
        old_missing_page_samples_are_not_direct_abba_evidence=True,
        actual_motion_cpu_or_fps_gain_proven=False,root_serial_device_window_required=True,
        preserve_latest_user_pause=True,production_modified=False,device_actions=False)
    (HERE/'HANDOFF_V24.json').write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    names=('V24_METADATA_BINDING.json','HANDOFF_V24.json','MEASUREMENT_BOUNDARY.txt','update_metadata.py')
    manifest={name:sha(HERE/name) for name in names}
    (HERE/'BINDING_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=HERE/'v24_metadata_measurement_binding.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as out:
        for name in (*names,'BINDING_MANIFEST.json'):out.write(HERE/name,name)
    receipt=dict(archive=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
        handoff_sha256=sha(HERE/'HANDOFF_V24.json'))
    (HERE/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    current_path=ANIM/'ANIMATION_DIRECTION_CURRENT.json'
    current=json.loads(current_path.read_text(encoding='utf-8'))
    current.update(status=report['status'],preferred_handoff='all_states_motion_v3_minimal/v24_binding/HANDOFF_V24.json',
        detail='all_states_motion_v3_minimal/v24_binding/MEASUREMENT_BOUNDARY.txt',
        current_metadata_startup=report['startup_sha256'],current_metadata_version='v24',
        local_validation_snapshot_startup=prior['final_v23_startup_sha256'],
        required_actual_integration_baseline='v24 metadata verified; 25 v23 tests carried because all26 dependencies unchanged; root rechecks current source/config before device window',
        current_pin_dependencies_checked=26,local_gate_tests=25,gate_tests_source_version='v23',
        tests_rerun_this_update=0,v24_metadata_package=receipt,
        business_abba_requires_main_visible_and_scheduling=True,physical_display_state_is_separate=True)
    current_path.write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(startup=report['startup_sha256'],changed_files=list(changes),
        unchanged_gate_dependencies=26,rendering_pins=len(render),tests_rerun=0,package=receipt)))


if __name__=='__main__':main()
