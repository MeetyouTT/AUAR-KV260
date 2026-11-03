"""Local public-source interface reconciliation and narrow synthetic probes.

Does not execute a CPU stop/history adapter, original loader, service, transport,
model, native library or real checkpoint. Baseline 65-case suite is not rerun.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CPU = HERE.parent / 'cpu_optimization_20261102'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def module_from(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def synthetic_prepare(tests, *, old_consumed=False, domain_consumed=False):
    (HERE / 'test_work').mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
    try:
        recovery = tests.FakeRecovery(temporary.name)
        runtime = tests.runtime
        real_lexists = runtime.os.path.lexists
        marker = '/public/kernel-history/kernel-boot-' + tests.BOOT + '.consumed'

        def lexists(path):
            text = str(path)
            if text.startswith(str(runtime.CHECKPOINT) + '.native-consumed-'):
                return old_consumed
            if text == marker:
                return domain_consumed
            return real_lexists(path)

        # Supply actual original marker metadata as contract input. The baseline
        # has no guard consuming this input; that difference is what is probed.
        recovery.contract['native_boot_policy'] = dict(allow_new_kernel_boot=True,
                                                      new_boot_marker_directory='/public/kernel-history')
        recovery.current_domain_consumed = lambda: domain_consumed
        with patch.object(runtime, 'regular', recovery.read), patch.object(runtime, 'create', tests.local_create), \
                patch.object(runtime, 'platform_metadata', lambda: recovery.plat.copy()), \
                patch.object(runtime, 'owner_scan', lambda **kw: tests.safe_scan()), \
                patch.object(runtime.os.path, 'lexists', lexists):
            try:
                result = recovery.prepare()
                outcome = result['status']
            except tests.rules.Hold as error:
                outcome = str(error)
        return dict(outcome=outcome, original_action_names=[e for e in recovery.events if e != 'verify_original_release'],
                    real_commands=0, real_native_validation=False)
    finally:
        tests.checked_cleanup(temporary)


def main():
    path = CPU / 'BOOT_RECOVERY_INTERFACE.json'
    before = path.read_bytes()
    interface = json.loads(before)
    checked = {}
    for role, artifact in interface['artifacts'].items():
        source = Path(artifact['path'])
        actual = digest(source.read_bytes())
        if actual != artifact['sha256']:
            raise RuntimeError('CPU artifact changed: ' + role)
        checked[role] = dict(path=str(source), sha256=actual, verified=True)
    adapter = module_from('cpu_pure_interface_for_boot_reconciliation', Path(interface['artifacts']['local_adapter']['path']))
    sys.path.insert(0, str(HERE / 'candidate'))
    tests = module_from('boot_interface_narrow_probe_helpers', HERE / 'tests/test_boot_recovery.py')
    original_flow = dict(schema='aura-boot-interface-observation-1', board_boot_id=tests.BOOT,
                         observation_provenance_required=True, camera_running=False,
                         no_live_camera_owner_confirmed=True,
                         checkpoint_pin=dict(path='/public/original-final.json', sha256='8' * 64),
                         checkpoint_source_boot=tests.PREVIOUS, allow_new_kernel_boot=True,
                         current_kernel_domain_consumed=False)
    cold_route = adapter.plan_flow(original_flow)
    source_consumed = synthetic_prepare(tests, old_consumed=True)
    current_consumed = synthetic_prepare(tests, domain_consumed=True)
    domain_flow = dict(original_flow, current_kernel_domain_consumed=True)
    try:
        adapter.plan_flow(domain_flow)
        original_domain_hold = False
    except adapter.RequiredMetadata:
        original_domain_hold = True
    blockers = []
    if source_consumed['outcome'] == 'CONSUMED_FINAL_POINTER':
        blockers.append(dict(id='CPU_INTERFACE_COLD_MARKER_FAMILIES', severity='blocker',
                             evidence='Different-boot archival input is rejected solely for a prior checkpoint-specific marker, although the original cold path checks the new kernel-domain marker.',
                             minimum_change='Separate same-boot consumed-final rejection from cold archive-only marker handling; retain explicit stale c6c8 rejection and all original reader/marker ownership.'))
    if original_domain_hold and current_consumed['outcome'] == 'ORIGINAL_WIDE_READY_IDSTOP_ONLY':
        blockers.append(dict(id='CPU_INTERFACE_CURRENT_DOMAIN_BEFORE_DFX', severity='blocker',
                             evidence='Synthetic prepare progresses through original list/remove/load/IDSTOP even when the actual configured current-domain marker exists.',
                             minimum_change='Capture original boot options/marker-directory metadata and reject consumed/partial/symlink current-domain marker before original DFX or camera start.'))
    if path.read_bytes() != before:
        raise RuntimeError('CPU interface changed during reconciliation')
    report = dict(schema='aura-boot-cpu-interface-reconciliation-1',
                  updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  interface_path=str(path), interface_sha256=digest(before),
                  status='SOURCE_HASHES_VERIFIED_ALIGNMENT_BLOCKS_FOUND' if blockers else 'LOCAL_INTERFACE_ALIGNMENT_PROBES_PASS',
                  artifacts_verified=checked, artifact_count=len(checked),
                  existing_adapter_hashes_match_candidate_reference=True,
                  original_cold_route=dict(route=cold_route['route'], normal_stop_required=False,
                                           same_boot_history_validator_applicable=False, original_loader_executed=False),
                  probes=dict(old_checkpoint_specific_marker=source_consumed, current_kernel_domain_marker=current_consumed),
                  blockers=blockers,
                  installation_scope='Current candidate capture is maintenance-running-only; it must remain separate from no-owner cold entry and cannot manufacture a stop receipt.',
                  independent_review=dict(path=str(CPU / 'BOOT_CANDIDATE_INDEPENDENT_REVIEW.json'),
                                          received=(CPU / 'BOOT_CANDIDATE_INDEPENDENT_REVIEW.json').exists()),
                  baseline_65_suite_rerun=False, candidate_sources_modified=False, board_calls=0,
                  CPU_adapters_or_Native_validators_executed=False, deployment_authorized=False)
    output = HERE / 'review/CPU_INTERFACE_RECONCILIATION.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    status_path = HERE / 'BOOT_RECOVERY_STATUS.json'
    status = json.loads(status_path.read_text(encoding='utf-8-sig'))
    status.update(updated_at_utc=report['updated_utc'],
                  phase='CPU_INTERFACE_ALIGNMENT_REPAIR_REQUIRED_REVIEW_PENDING' if blockers else 'CPU_INTERFACE_ALIGNMENT_FIXED_INDEPENDENT_REVIEW_PENDING',
                  cpu_interface_reconciliation=dict(state=report['status'], receipt='review/CPU_INTERFACE_RECONCILIATION.json',
                                                    interface_sha256=report['interface_sha256'], verified_artifacts=len(checked),
                                                    blockers=[row['id'] for row in blockers], baseline_not_rerun=True,
                                                    candidate_changed_since_review_snapshot=True,
                                                    current_revision_not_yet_packaged=True),
                  ready_to_execute=False)
    status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], verified_artifacts=len(checked),
                          blockers=[row['id'] for row in blockers], baseline_65_suite_rerun=False, board_calls=0)))


if __name__ == '__main__':
    main()
