"""Record local fixes against the CPU's frozen review; never claim its approval."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CPU = HERE.parent / 'cpu_optimization_20261102'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    review_path = CPU / 'BOOT_CANDIDATE_INDEPENDENT_REVIEW.json'
    review_raw = review_path.read_bytes()
    review = json.loads(review_raw)
    if review.get('review_complete') is not True:
        raise RuntimeError('Complete independent review required')
    validation_path = HERE / 'validation/LOCAL_VALIDATION.json'
    validation = json.loads(validation_path.read_bytes())
    if validation['status'] != 'PASS_OFFLINE_TARGETED_REVISION' or validation['failed'] or validation['errors']:
        raise RuntimeError('Successful current targeted checks required')
    for path, pin in validation['source_sha256'].items():
        if digest((HERE / path).read_bytes()) != pin:
            raise RuntimeError('Validated source changed: ' + path)
    source_snapshot = HERE / 'evidence/CPU_INDEPENDENT_REVIEW_REVISION2.json'
    source_snapshot.write_bytes(review_raw)
    fixes = {
        'B01_RELEVANT_QUEUED_PLATFORM_JOBS': ('quiet / daemon_owner', 'Always checks complete queued jobs, including no-process DFX and daemon lifecycle jobs; exact owned starts only.', 'test_review_job_queue.py'),
        'B02_CAMERA_EXITING_OR_QUIESCED_USED_FOR_BINDING': ('camera_samples / check_camera_live / bind_camera / verify_gui', 'Exact active/running/no-job/control-owner and nonquiesced state, rechecked before source CAS, ledger publication and READY.', 'test_review_binding_and_health.py'),
        'B03_ACTIVE_LEDGER_EXPECTED_BYTES_DRIFT': ('source_snapshot / bind_camera', 'Captures ledger existence/raw bytes with the initial source snapshot, rechecks before source mutation and uses those same bytes in final CAS.', 'test_review_binding_and_health.py'),
        'B04_EXACT_FINAL_COMPLETE_HISTORY_NOT_RUNTIME_BOUND': ('check_prestart_history / original_history_gate / accepted_live_history', 'Every exact final is bound to unchanged original CPU reader/bounds/archive APIs and independent ordered history. Real prior complete result required for same-boot. Original consumption/archive/kernel-marker linkage and full new chain checked before binding/READY.', 'test_review_history_gate.py'),
        'B05_HANDOFF_MODE_NOT_DERIVED_FROM_BOOT_RELATION': ('verify_bootstrap_handoff', 'Required handoff mode is derived from predecessor/current boot relation; inconsistent mode cannot select a weaker check.', 'test_cpu_interface_alignment.py'),
    }
    rows = []
    for finding in review['blocking_findings']:
        functions, detail, tests = fixes[finding['id']]
        rows.append(dict(id=finding['id'], reviewed_source_sha256=finding['sha256'],
                         disposition='IMPLEMENTED_TARGETED_CHECKS_PASS_REQUIRES_NEW_INDEPENDENT_REVIEW',
                         functions=functions, change=detail, targeted_tests='tests/' + tests))
    resolution = dict(schema='aura-boot-candidate-independent-review-resolution-3',
                      updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      source_review=dict(path=str(review_path), sha256=digest(review_raw), complete=True,
                                         verdict=review['verdict'], frozen_revision='observed revision2'),
                      repaired_revision='local revision3', blocking_findings=rows,
                      recovery_limit_fix=dict(id='L01_ACTIVE_AFTER_BEFORE_COMMITTED',
                                             disposition='Preseals exact after-ledger bytes/SHA before publication; guarded rollback works without a committed receipt.',
                                             tests='tests/test_review_commit_gap.py'),
                      retained_scope=dict(id='S01_UNCLEAN_POWER_LOSS_FAIL_CLOSED',
                                          coverage='Clean normal-shutdown cold recovery. Missing/latest-owner-mismatched final after unclean power loss stays HOLD; no guessed owner/counter or marker edits.'),
                      validation=dict(path='validation/LOCAL_VALIDATION.json', sha256=digest(validation_path.read_bytes()),
                                      targeted_tests_run=validation['tests_run'], failed=0, errors=0,
                                      baseline_65_suite_rerun=False, original_Native_validators_executed=False),
                      current_source_sha256=validation['source_sha256'],
                      repaired_revision_independently_approved=False, new_hash_review_required=True,
                      live_metadata_and_exclusive_handoff_required=True,
                      device_operations=0, deployed=False, cold_boot_accepted=False)
    output = HERE / 'review/INDEPENDENT_REVIEW_RESOLUTION.json'
    output.write_text(json.dumps(resolution, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='FIVE_REVIEW_FINDINGS_IMPLEMENTED_NEW_HASH_REVIEW_REQUIRED',
                          targeted_tests=validation['tests_run'], independently_approved=False, deployed=False)))


if __name__ == '__main__':
    main()
