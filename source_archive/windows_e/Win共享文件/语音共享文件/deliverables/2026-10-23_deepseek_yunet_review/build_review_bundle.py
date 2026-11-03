"""Build a local, curated source/evidence review packet; no network or device IO."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件')
DELIVERIES = SHARED / 'deliverables'
FORMAL = DELIVERIES / '2026-10-23_sface_formal_dpu'
AUDIT = Path('/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/evidence/ubuntu/project_remaining_20261023.json')
EXCLUDED_NAMES = {'DeepSeek_YuNet审查包.zip', 'DeepSeek_YuNet审查资料.txt',
                  'build_review_bundle.py', 'CHECKS.json', 'SHA256SUMS.json'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def read_record(path):
    raw = path.read_bytes()
    return json.loads(raw), {'source': str(path), 'sha256': digest(raw)}


def main():
    manifest, manifest_input = read_record(FORMAL / 'ACTIVE_RELEASE.json')
    audit, audit_input = read_record(AUDIT)
    snapshot = audit['snapshot']
    assert snapshot['unit_sha256'] == manifest['unit_sha256']
    assert manifest['accepted'] and manifest['formal_identity_backend'] == 'DPU_SFACE_INT8'
    index = []

    def add_source(source, relative, verification, expected=None):
        raw = source.read_bytes()
        sha = digest(raw)
        if expected is not None:
            assert sha == expected, 'SHA mismatch: ' + str(source)
        if relative.endswith('.py'):
            ast.parse(raw.decode('utf-8'), filename=relative)
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        index.append({'path': relative, 'source': str(source), 'sha256': sha,
                      'bytes': len(raw), 'verification': verification,
                      'release_pin': expected})

    current_paths = set()
    for relative, record in manifest['active_source_files'].items():
        add_source(FORMAL / 'active_source' / relative, 'current_source/' + relative,
                   'DEPLOYED_SOURCE_EXPORT_MATCHES_ACTIVE_RELEASE_SHA256', record['sha256'])
        if relative.startswith('aura/'):
            current_paths.add(relative[len('aura/'):])
    for relative, sha in manifest['candidate_pins'].items():
        if relative in current_paths:
            continue
        add_source(FORMAL / 'source/candidate/aura' / relative,
                   'release_pinned_source/aura/' + relative,
                   'MATCHES_ACCEPTED_CANDIDATE_PIN_NOT_NEW_BOARD_EXPORT', sha)

    supporting = [
        (Path('/home/ghmd/aura-thread-sched-20261022/candidate/aura/board/vision/pipeline_metrics.py'), 'aura/board/vision/pipeline_metrics.py'),
        (Path('/home/ghmd/aura-thread-sched-20261022/candidate/aura/board/vision/thread_sched_metrics.py'), 'aura/board/vision/thread_sched_metrics.py'),
        (SHARED / 'aura/board/vision/yolo_dpu.py', 'aura/board/vision/yolo_dpu.py'),
        (SHARED / 'aura/board/vision/person_bytetrack.py', 'aura/board/vision/person_bytetrack.py'),
        (SHARED / 'aura/board/vision/local_preview.py', 'aura/board/vision/local_preview.py'),
        (SHARED / 'aura/board/interaction/ui_contract.py', 'aura/board/interaction/ui_contract.py'),
    ]
    for source, relative in supporting:
        add_source(source, 'supporting_source/' + relative,
                   'REFERENCE_SOURCE_ONLY_NO_CURRENT_BOARD_SHA_PIN_IN_THIS_PACKET')
    tests = [
        (FORMAL / 'source/tests/test_sface_notification.py', 'formal/test_sface_notification.py'),
        (FORMAL / 'source/tests/test_slot_retry.py', 'formal/test_slot_retry.py'),
        (Path('/home/ghmd/aura-yunet-slot-wait-20261023/tests/test_slot_wait.py'), 'yunet/test_slot_wait.py'),
        (Path('/home/ghmd/aura-yunet-slot-wait-20261023/tests/test_slot_wait_integration.py'), 'yunet/test_slot_wait_integration.py'),
        (Path('/home/ghmd/aura-yunet-bounded-recovery-20261023/tests/test_bounded_recovery.py'), 'recovery/test_bounded_recovery.py'),
        (Path('/home/ghmd/aura-thread-sched-20261022/timing-tests/tests/test_pipeline_metrics.py'), 'timing/test_pipeline_metrics.py'),
        (Path('/home/ghmd/aura-thread-sched-20261022/timing-tests/tests/test_thread_sched_metrics.py'), 'timing/test_thread_sched_metrics.py'),
    ]
    for source, relative in tests:
        add_source(source, 'tests_reference/' + relative,
                   'EXISTING_TEST_FOR_REVIEW_NOT_EXECUTED_IN_THIS_PACKET_BUILD')

    schedule = snapshot['schedule']
    events = schedule['optional_diagnostics']['fault_events']
    assert len(events) == 2
    phases = []
    for event in events:
        phase = {
            'pre_execute_ms': (event['execute_start_mono_ns'] - event['optional_start_mono_ns']) / 1e6,
            'execute_api_ms': event['execute_wall_ms'],
            'between_execute_return_and_wait_ms': (event['wait_start_mono_ns'] - event['execute_return_mono_ns']) / 1e6,
            'wait_api_ms': event['wait_wall_ms'],
            'after_wait_ms': (event['optional_end_mono_ns'] - event['wait_end_mono_ns']) / 1e6,
        }
        assert abs(sum(phase.values()) - event['optional_wall_ms']) < 1e-6
        phases.append({'event_sequence': event['event_sequence'],
                       'scheduler_occupancy_ms': event['scheduler_occupancy_ms'],
                       'diagnostic_optional_wall_ms': event['optional_wall_ms'],
                       'derived_fault_phases_ms': phase,
                       'native_status': event['native_status'],
                       'native_completed': event['native_completed']})
    write_json(ROOT / 'evidence/latest_yunet_faults.json', {
        'source_provenance': audit_input,
        'response_host_utc': audit['response_host_utc'],
        'audit_host_utc': audit['audit_host_utc'],
        'unit_sha256': snapshot['unit_sha256'],
        'camera_pid': snapshot['camera']['pid'],
        'camera': snapshot['camera'],
        'services': snapshot['services'],
        'schedule': schedule,
        'identity': snapshot['identity'],
        'freshness_counters': snapshot['faces']['freshness_metrics']['counters'],
        'cpu_sample': snapshot['cpu_sample'],
        'current_usb_kernel_warnings_sampled': audit['current_usb_kernel_warnings_sampled'],
        'derived_events': phases,
        'limitation': 'Recorded read-only snapshot, not a new live query; no current USB fault window was collected.'})

    write_json(ROOT / 'evidence/current_release_summary.json', {
        'source_provenance': manifest_input,
        **{key: manifest[key] for key in ['unit_sha256', 'camera_pid', 'audio_pid',
            'xserver_pid', 'accepted', 'scope', 'formal_identity_backend', 'face_backend',
            'body_detector_backend', 'candidate_pins', 'active_source_files']},
        'model_fingerprint': '0x101000056010407',
        'long_duration_and_cold_start_acceptance': 'NOT_ESTABLISHED_BY_THIS_REVIEW_PACKET'})

    older_path = DELIVERIES / '2026-10-23_runtime_overrun_recheck/current-status.json'
    older, older_input = read_record(older_path)
    write_json(ROOT / 'evidence/historical_overrun_before_recovery.json', {
        'scope': 'HISTORICAL_PREVIOUS_RELEASE_NOT_CURRENT', 'source_provenance': older_input,
        **{key: older[key] for key in ['unit_sha256', 'camera_pid', 'camera_process_age_s',
            'yunet_schedule', 'fault_events', 'usb_warning_query', 'primary_period_overruns'] if key in older}})
    prior_path = DELIVERIES / '2026-10-23_cpu_dpu_diagnosis/evidence.json'
    prior, prior_input = read_record(prior_path)
    write_json(ROOT / 'evidence/historical_lock_and_counter_findings.json', {
        'scope': 'HISTORICAL_REJECTED_CANDIDATE_AND_OLDER_ACCEPTED_RELEASE',
        'source_provenance': prior_input,
        'rejected_first_candidate': prior['rejected_first_candidate'],
        'old_normal_trace': prior['maximum_normal_trace'],
        'baseline_gap_before': prior['baseline_window']['gap_intervals_before'],
        'baseline_gap_after': prior['baseline_window']['gap_intervals_after'],
        'baseline_new_gaps': prior['baseline_window']['new_gap_intervals']})
    write_json(ROOT / 'source_index.json', {
        'built_host_utc': datetime.now(timezone.utc).isoformat(),
        'current_unit_sha256': manifest['unit_sha256'], 'entries': index,
        'not_an_executable_release': True,
        'missing_runtime_material': ['installed VART/XIR libraries and matching binding source',
            'complete GUI runtime and current function-level CPU profile',
            'current fault-aligned USB/kernel/runqueue timing', 'model weights and real camera inputs']})

    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.name not in EXCLUDED_NAMES)
    sums = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in files}
    write_json(ROOT / 'SHA256SUMS.json', sums)
    prompt = (ROOT / '给DeepSeek的完整提示词.md').read_text()
    chunks = [prompt, '\n\n以下为附件源码与数值证据。源文件行号从1开始；身份/模型数据未附。\n']
    for path in files:
        if path.name == '给DeepSeek的完整提示词.md':
            continue
        relative = path.relative_to(ROOT).as_posix()
        chunks.append('\n' + '=' * 72 + '\nFILE: ' + relative + '\nSHA256: ' + sums[relative] + '\n' + '=' * 72 + '\n')
        body = path.read_text()
        if path.suffix == '.py':
            chunks.append('\n'.join(f'{number:04d}: {line}' for number, line in enumerate(body.splitlines(), 1)) + '\n')
        else:
            chunks.append(body)
    combined = ROOT / 'DeepSeek_YuNet审查资料.txt'
    combined.write_text(''.join(chunks))
    archive = ROOT / 'DeepSeek_YuNet审查包.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for path in [*files, ROOT / 'SHA256SUMS.json']:
            output.write(path, arcname=path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as output:
        assert output.testzip() is None
        for relative, sha in sums.items():
            assert digest(output.read(relative)) == sha
    checks = {
        'source_files': len(index),
        'deployed_source_export_hashes_verified': sum(item['verification'].startswith('DEPLOYED_') for item in index),
        'additional_release_pins_verified': sum(item['verification'].startswith('MATCHES_') for item in index),
        'supporting_unpinned_sources': len(supporting), 'reference_tests': len(tests),
        'python_ast_files_checked': sum(item['path'].endswith('.py') for item in index),
        'fault_timelines_recomputed': len(phases), 'archive_entries': len(files) + 1,
        'archive_crc_and_sha_verified': True,
        'combined_text_bytes': combined.stat().st_size,
        'archive_bytes': archive.stat().st_size,
        'archive_sha256': digest(archive.read_bytes()),
        'new_board_commands': 0, 'new_inference_jobs': 0, 'production_changes': 0,
        'external_uploads_or_messages': 0}
    write_json(ROOT / 'CHECKS.json', checks)
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == '__main__':
    main()
