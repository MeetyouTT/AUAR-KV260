"""Archive numeric board evidence and frozen candidates; never copy biometric data."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/home/ghmd')
SHARED = BASE / 'Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_live_baseline'
PROBES = BASE / 'aura-model-inventory-20261021'


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def pinned_copy(source, target):
    data = source.read_bytes()
    if target.exists():
        assert target.read_bytes() == data, 'Refusing to overwrite different file: ' + str(target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def successful_probe(name):
    status = read_json(PROBES / (name + '.status.json'))
    assert status['exit_code'] == 0 and status['console_echo_restored']
    return read_json(PROBES / (name + '.response.json'))


def main():
    collected = successful_probe('sface_shadow_final_collect')
    report = collected['report']
    audit = successful_probe('yunet_active_release_audit')
    release = read_json(SHARED / 'release.json')
    assert report['passed'] and report['complete'] and report['rollback_verified']
    assert not report['rollback_timer_left_armed'] and report['ui_pid_preserved']
    assert len(report['samples']) == 20
    assert report['shadow_completed'] == report['shadow_accepted'] == 10
    assert not report['identity_backend_changed'] and not report['identity_database_configuration_changed']
    shadow = report['camera_after']['shadow']
    assert shadow['failures'] == shadow['stale'] == shadow['identity_decisions_from_shadow'] == shadow['templates_written'] == 0
    assert audit['source_hashes'] == release['yunet']['candidate_source_sha256']
    assert audit['camera_unit_sha256'] == report['baseline_unit_sha256']
    assert audit['runtime'] == report['baseline_runtime']
    assert audit['pid'] == report['restored']['pid'] == 165277
    assert audit['sface_shadow_absent'] and audit['cu_collector_inactive'] and audit['detection_advanced']
    assert not audit['active_owned_rollback_timers']
    assert audit['original_database_path_preserved'] and audit['face_backend_hashes_verified']
    assert audit['feature_backend']['kind'] == 'windows_sface'
    assert 'MainPID=131932' in audit['units']['aura-avatar-ui.service']
    assert 'MainPID=1077' in audit['units']['xserver-nodm.service']

    old_audit = SHARED / 'evidence/active-release-audit.json'
    preserved = SHARED / 'evidence/active-release-audit-pre-shadow.json'
    if not preserved.exists():
        assert read_json(old_audit)['pid'] == 134844
        pinned_copy(old_audit, preserved)
    write_json(old_audit, audit)
    write_json(SHARED / 'evidence/sface-shadow-pilot-full.json', report)
    write_json(SHARED / 'evidence/sface-shadow-pilot-provenance.json', {
        'board_report_path': collected['path'], 'board_report_sha256': collected['sha256'],
        'shared_report_format': 'Parsed JSON, reindented; original board bytes SHA above',
        'transport_exit_code': 0, 'console_echo_restored': True,
        'images_audio_embeddings_identity_database_included': False,
        'source_patch_sha256': report['patch_sha256'],
    })
    for name in ['sface_visual_readiness', 'sface_network_readiness', 'sface_shadow_readiness']:
        data = successful_probe(name)
        write_json(SHARED / ('evidence/' + name + '.json'), data)

    for name in ['sface_shadow_final_collect.py', 'yunet_active_release_audit.py']:
        pinned_copy(PROBES / name, SHARED / 'source' / name)
    pinned_copy(BASE / 'aura-identity-dpu-check-20261018/board_sface_shadow_pilot_20261022.py',
                SHARED / 'source/board_sface_shadow_pilot_20261022.py')
    pinned_copy(BASE / 'aura-dpu-vision-20261021/work/sface-shadow-deploy-patch.tar.gz',
                SHARED / 'source/sface-shadow-deploy-patch.tar.gz')
    prep = BASE / 'aura-sface-shadow-candidate-20261021/deploy-preparation'
    for source in sorted(prep.iterdir()):
        if source.is_file():
            pinned_copy(source, SHARED / 'sface-shadow-candidate/deploy-preparation' / source.name)

    now = datetime.now(timezone.utc).isoformat()
    release['updated_utc'] = now
    release['status'] = 'YUNET_LIVE_30MIN_RETAINED_SFACE_REAL_FACE_SHADOW_PASSED_REVERTED'
    release['runtime']['camera_pid'] = audit['pid']
    release['sface'].update({
        'shadow_candidate_software_tests': 16,
        'shadow_deployment_preparation_local_tests': 3,
        'shadow_board_verified': True,
        'shadow_production_enabled': False,
        'shadow_validation_scope': '20-second real face shared YOLO/YuNet/SFace DPU execution; always restored to retained YuNet baseline; no identity accuracy acceptance',
        'shadow_observation_s': 20,
        'shadow_completed': report['shadow_completed'],
        'shadow_accepted_by_target_and_freshness': report['shadow_accepted'],
        'shadow_feature_call_latency_ms': shadow['accepted_latency_ms'],
        'shadow_dpu_schedule_maximum_ms': report['camera_after']['dpu_schedule']['optional']['sface']['maximum_ms'],
        'shadow_observed_yolo_hz': report['observed_yolo_hz'],
        'shadow_observed_yunet_hz': report['observed_yunet_hz'],
        'shadow_cpu_pct_board': report['pilot_cpu_total']['cpu_percent_of_board'],
        'shadow_compare_cosine': False,
        'shadow_identity_decisions': 0,
        'shadow_templates_written': 0,
        'shadow_rollback_verified': True,
        'direct_identity_runtime_business_board_verified': False,
        'shadow_xrt_busy_percent_measured': False,
    })
    release['verification']['sface_shadow_absent_after_pilot'] = audit['sface_shadow_absent']
    release['evidence'].update({
        'sface_shadow_real_face': 'evidence/sface-shadow-pilot-full.json',
        'sface_shadow_provenance': 'evidence/sface-shadow-pilot-provenance.json',
        'sface_shadow_report': 'SFace_真人影子短测.md',
        'pre_shadow_audit': 'evidence/active-release-audit-pre-shadow.json',
    })
    write_json(SHARED / 'release.json', release)
    print(json.dumps({'status': release['status'], 'camera_pid': audit['pid'],
                      'shadow_completed': report['shadow_completed'], 'source_and_rollback_verified': True}))


if __name__ == '__main__':
    main()
