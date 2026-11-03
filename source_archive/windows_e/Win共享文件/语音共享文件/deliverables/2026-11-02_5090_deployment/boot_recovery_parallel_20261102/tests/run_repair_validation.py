"""Run only changed review boundaries and their direct integration checks."""
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))


def load(name):
    path = HERE / 'tests' / (name + '.py')
    spec = importlib.util.spec_from_file_location('final_repair_' + name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def add_cases(suite, klass, names=None):
    if names is None:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(klass))
    else:
        suite.addTests(klass(name) for name in names)


def main():
    (HERE / 'test_work').mkdir(exist_ok=True)
    baseline_path = HERE / 'validation/baseline65_v1/LOCAL_VALIDATION.json'
    baseline = json.loads(baseline_path.read_bytes())
    marker, jobs = load('test_cpu_interface_alignment'), load('test_review_job_queue')
    binding, history, gap = load('test_review_binding_and_health'), load('test_review_history_gate'), load('test_review_commit_gap')
    helpers = marker.helpers
    suite = unittest.TestSuite()
    add_cases(suite, marker.CpuInterfaceMarkerTests)
    add_cases(suite, jobs.PendingJobTests)
    add_cases(suite, binding.CameraAdmissionTests)
    add_cases(suite, binding.CapturedLedgerTests, [
        'test_normal_binding_publishes_captured_ledger',
        'test_ledger_change_after_source_capture_aborts_before_ui_write',
        'test_ledger_change_after_ui_startup_writes_is_never_reblessed',
        'test_camera_lifecycle_change_immediately_before_cas_keeps_sources_original'])
    add_cases(suite, history.OriginalHistoryCallThroughTests)
    add_cases(suite, gap.CommitGapTests, [
        'test_active_publication_without_committed_receipt_still_has_known_after_bytes',
        'test_tampered_after_snapshot_cannot_authorize_rollback'])
    add_cases(suite, helpers.PrepareTests, [
        'test_camera_gate_records_exact_final_without_consuming_or_rewriting_it',
        'test_camera_gate_refuses_a_consumed_same_boot_pointer_before_original_start'])
    add_cases(suite, helpers.OnceTests, [
        'test_unknown_submission_is_durable_and_never_resent',
        'test_durable_intent_precedes_dispatch_and_success_reentry_only_observes'])
    add_cases(suite, helpers.PackagingTests, [
        'test_python39_candidate_syntax', 'test_no_new_motion_or_forced_lifecycle_entry',
        'test_effective_candidate_dependency_graph_is_acyclic_and_ordered'])
    add_cases(suite, helpers.SourceDriftTests, [
        'test_new_identity_release_requires_fresh_sealing', 'test_selected_camera_source_change_is_not_accepted'])
    ids = []
    def collect(node):
        for item in node:
            if isinstance(item, unittest.TestSuite):
                collect(item)
            else:
                ids.append(item.id())
    collect(suite)
    log = HERE / 'validation/repair_final_revision3.log'
    with log.open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    files = [p for p in (HERE / 'candidate').rglob('*') if p.is_file()]
    files += list((HERE / 'tests').glob('*.py'))
    receipt = dict(schema='aura-boot-recovery-offline-targeted-revision-3',
                   updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status='PASS_OFFLINE_TARGETED_REVISION' if result.wasSuccessful() else 'FAIL',
                   tests_run=result.testsRun, failed=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                   baseline_validation=dict(path=baseline_path.relative_to(HERE).as_posix(), tests_run=baseline['tests_run'],
                                            sha256=hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                                            scope='65 cases on original v1; not applied to new hashes'),
                   baseline_65_suite_rerun=False, selected_case_ids=ids, log=log.relative_to(HERE).as_posix(),
                   source_sha256={p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
                   board_calls=0, hardware_or_model_loads=0, real_databases_opened=0,
                   original_Native_validators_executed=False,
                   limitations=['History-call tests use synthetic API doubles, not actual Native validation',
                                'Independent review covers its frozen revision; repaired hashes need a new review',
                                'Fresh target systemd/loader/owner/history evidence remains required'],
                   deployed=False, cold_boot_accepted=False)
    (HERE / 'validation/LOCAL_VALIDATION.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'], changed_boundary_tests=result.testsRun,
                          failed=len(result.failures), errors=len(result.errors), baseline_65_suite_rerun=False, board_calls=0)))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
