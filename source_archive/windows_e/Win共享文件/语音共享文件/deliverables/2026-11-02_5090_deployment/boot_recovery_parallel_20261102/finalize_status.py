"""Publish only this task's local handoff after checking sealed deliverables."""
import datetime
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def raw_json(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))


def atomic(name, value):
    target = HERE / name
    require_target = target.resolve()
    if require_target.parent != HERE.resolve():
        raise RuntimeError('Status target escaped this task directory')
    temporary = target.with_name(target.name + '.local-tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def main():
    validation = raw_json('validation/LOCAL_VALIDATION.json')
    packages = raw_json('PACKAGE_OUTPUTS.json')
    if validation['status'] not in {'PASS_OFFLINE_ONLY', 'PASS_OFFLINE_TARGETED_REVISION'} or validation['failed'] or validation['errors']:
        raise RuntimeError('Offline validation failed')
    for relative, expected in validation['source_sha256'].items():
        if hashlib.sha256((HERE / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Validated source changed')
    for artifact in packages['artifacts']:
        if hashlib.sha256((HERE / artifact['path']).read_bytes()).hexdigest() != artifact['sha256']:
            raise RuntimeError('Sealed archive changed')
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resolution_path = HERE / 'review/INDEPENDENT_REVIEW_RESOLUTION.json'
    resolution = json.loads(resolution_path.read_bytes()) if resolution_path.exists() else None
    phase = ('REPAIRED_REVISION3_PACKAGED_AWAITING_CPU_NEW_HASH_REVIEW' if resolution
             else 'OFFLINE_CANDIDATE_COMPLETE_AWAITING_FRESH_MAIN_HANDOFF')
    fresh = [
        dict(id='maintenance_rights', required='Identity explicitly returns idle maintenance rights; original main serializes main/axis/CPU access. Elapsed time is not a handoff.'),
        dict(id='actual_sources_and_owners', required='Latest actual boot, startup + all component pins, current selected source set and camera/GUI lifetimes after any identity/GTK changes. capture_contract.py collects the public source closure.'),
        dict(id='original_native_lifecycle', required='Capture the original CPU complete result AND its exact expected-input pin/independent ordered history; retain staged original5ca adapter. Each cold final uses archive-only validation and current-kernel marker linkage. Same-boot restart requires genuine4a5/5ca pins plus original reader/bounds recheck under the owned ordered prestart; no manufactured stop/Native state.'),
        dict(id='auxiliary_loader', required='Fresh dpu-auto-config.service generated unit and original init/helper source/ordering, or proven current absence. Existing evidence lists the unit but does not contain its body.'),
        dict(id='target_systemd', required='Actual target systemd-analyze verify, merged ExecStartPre/Requires/After, retained Native no-kill/infinite-stop properties and list-jobs column semantics. Installer refuses activation if graph verification fails.'),
        dict(id='cold_boot_software_receipt', required='One actual new-boot platform/camera/GUI READY receipt, same-platform original ID_STOP_ONLY flags0/lease0, no register owner, mechanically locked UI and no automatic reference/center/follow. No repeated human axis-follow acceptance is requested.'),
    ]
    steering = dict(axis_follow_and_no_stutter_human_accepted=True, axis_implementation_and_parameters_retained=True,
                    axis_repeated_motion_or_tuning_required_by_this_task=False,
                    face_voice_cross_modal_linking='cancelled_not_a_prerequisite',
                    independent_voice='identity chat responsibility',
                    benchmark_observation_scope='Saved historical evidence only; no assertion about the platform during the latest user test')
    handoff = dict(schema='aura-boot-recovery-parallel-handoff-1', updated_utc=now,
                   client_date='2026-11-02', timezone='America/Los_Angeles',
                   phase=phase,
                   offline_preparation_complete=True, ready_for_main_review=True, ready_to_execute=False,
                   activated=False, deployed=False, cold_boot_accepted=False,
                   completed=['Original default_accel/daemon dependency evidence with saved remote SHA comparison',
                              'Concrete original-client/systemd startup barriers and metadata-only fresh binding candidate',
                              'Fresh contract capture, add-only installation, target graph gate and exact-byte rollback',
                              'Public/synthetic Windows regressions and two verified source/rollback archives'],
                   validation=dict(path='validation/LOCAL_VALIDATION.json', tests_run=validation['tests_run'],
                                   failures=validation['failed'], errors=validation['errors'],
                                   scope='Current changed-boundary Windows tests; original65 v1 baseline retained, not rerun',
                                   baseline_validation=validation.get('baseline_validation'),
                                   original_Native_validators_executed=False),
                   evidence='evidence/SOURCE_AUDIT.json', source_comparison='review/ORIGINAL_SOURCE_COMPARISON.json',
                   diff='review/CANDIDATE_ADDITIONS.diff', review='REVIEW.txt', rollback='ROLLBACK.txt',
                   human_handoff='HANDOFF.txt', fresh_handoff_template='FRESH_HANDOFF.example.json',
                   packages=packages['artifacts'], fresh_metadata_required=fresh, latest_user_steering=steering,
                   cpu_adapters_reused_by_reference=raw_json('candidate/cpu_adapters.reference.json')['adapters'],
                   authorized_device_operations_performed=[], board_queries=0, ssh_calls=0,
                   real_database_audio_image_key_access=False, hardware_or_model_loads=0,
                   global_documents_or_production_or_peer_candidates_modified=False,
                   models_and_storage='Original 27B IQ4_XS / OmniVoice16, identity fixes, GTK optimization and D:/AIModels convention retained')
    if resolution:
        handoff['independent_review'] = dict(source_review=resolution['source_review'],
                                           resolution='review/INDEPENDENT_REVIEW_RESOLUTION.json',
                                           repaired_revision_independently_approved=False, new_hash_review_required=True)
    atomic('BOOT_RECOVERY_HANDOFF.json', handoff)
    status = raw_json('BOOT_RECOVERY_STATUS.json')
    status.update(updated_at_utc=now, phase=handoff['phase'], offline_preparation_complete=True,
                  ready_for_main_review=True, ready_to_execute=False, activated=False, deployed=False,
                  cold_boot_accepted=False,
                  tests=dict(state=validation['status'], passed=validation['tests_run'], failed=validation['failed'],
                             errors=validation['errors'], receipt='validation/LOCAL_VALIDATION.json',
                             baseline_validation=validation.get('baseline_validation'), baseline_65_suite_rerun=False,
                             scope='Changed review boundaries only; historical65 is not a current-hash result'),
                  missing_fresh_evidence=[item['required'] for item in fresh],
                  latest_user_steering=steering, handoff='BOOT_RECOVERY_HANDOFF.json', human_handoff='HANDOFF.txt',
                  packages=packages['artifacts'], source_comparison=handoff['source_comparison'], diff=handoff['diff'],
                  next_owner='Original main chat coordinates the explicit identity -> main/axis/CPU maintenance handoff; this branch dispatched no device operation')
    if resolution:
        status['independent_review'] = handoff['independent_review']
        status['cpu_interface_reconciliation'] = dict(state='INTERFACE_ALIGNED_LOCAL_REPAIRS_PACKAGED_NEW_HASH_REVIEW_REQUIRED',
                                                      receipt='review/CPU_INTERFACE_RECONCILIATION.json',
                                                      verified_artifacts=16, resolution='review/INDEPENDENT_REVIEW_RESOLUTION.json',
                                                      baseline_65_suite_rerun=False)
    atomic('BOOT_RECOVERY_STATUS.json', status)
    print(json.dumps(dict(phase=status['phase'], tests_passed=validation['tests_run'],
                          ready_for_review=True, ready_to_execute=False, deployed=False, cold_boot_accepted=False)))


if __name__ == '__main__':
    main()
