"""Build task-local review artifacts; no remote access or production writes."""
import ast
import datetime
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def zip_verified(path, files):
    snapshots = {p.relative_to(HERE).as_posix(): p.read_bytes() for p in sorted(set(files))}
    for name in snapshots:
        if any(part in {'test_work', '__pycache__', '.pytest_cache'} for part in Path(name).parts):
            raise RuntimeError('Transient test files cannot enter a delivery archive')
        if Path(name).suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.wav', '.mp3', '.png', '.jpg', '.gguf', '.bin', '.so'}:
            raise RuntimeError('Private/media/model/binary payload refused')
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in snapshots.items():
            archive.writestr(name, raw)
    with zipfile.ZipFile(path, 'r') as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(snapshots):
            raise RuntimeError('Archive integrity failed')
        for name, raw in snapshots.items():
            if archive.read(name) != raw:
                raise RuntimeError('Archive differs from reviewed local bytes')
    return dict(path=path.name, sha256=sha(path.read_bytes()), bytes=path.stat().st_size,
                files=len(snapshots), exact_bytes_verified=True)


def main():
    import sys
    sys.path.insert(0, str(HERE / 'candidate'))
    install = module_at('boot_recovery_local_packager', HERE / 'candidate/manage_installation.py')
    validation = json.loads((HERE / 'validation/LOCAL_VALIDATION.json').read_bytes())
    if validation['status'] not in {'PASS_OFFLINE_ONLY', 'PASS_OFFLINE_TARGETED_REVISION'} or validation['failed'] or validation['errors']:
        raise RuntimeError('A successful final offline validation receipt is required')
    for relative, pin in validation['source_sha256'].items():
        if sha((HERE / relative).read_bytes()) != pin:
            raise RuntimeError('Source changed after final validation: ' + relative)
    for path in (HERE / 'candidate').glob('*.py'):
        ast.parse(path.read_bytes(), feature_version=(3, 9))
    # Preserve the actual old65 archives, rather than relabeling them as a
    # successful validation of the repaired working tree.
    baseline_dir = HERE / 'validation/baseline65_v1'
    if (HERE / 'PACKAGE_OUTPUTS.json').exists() and baseline_dir.exists():
        previous_outputs = json.loads((HERE / 'PACKAGE_OUTPUTS.json').read_bytes())
        saved_index = baseline_dir / 'PACKAGE_OUTPUTS.json'
        if not saved_index.exists():
            for artifact in previous_outputs['artifacts']:
                raw = (HERE / artifact['path']).read_bytes()
                if sha(raw) != artifact['sha256']:
                    raise RuntimeError('Original sealed archive changed before preservation')
                (baseline_dir / artifact['path']).write_bytes(raw)
            saved_index.write_bytes((HERE / 'PACKAGE_OUTPUTS.json').read_bytes())
    example = (HERE / 'candidate/contract.example.json').read_bytes()
    payload = install.payload(example)
    if json.loads(example)['fresh_handoff_approved'] or (HERE / 'candidate/activation.json').exists():
        raise RuntimeError('Offline candidate must remain unactivated')
    review = HERE / 'review'
    review.mkdir(exist_ok=True)
    diff = ['# OFFLINE ADDITIONS ONLY. contract.json below is the INERT example; fresh capture is mandatory.\n',
            '# No original service, startup launcher, default firmware, Native source or private store is replaced.\n']
    for target, raw in sorted(payload.items()):
        diff.extend(difflib.unified_diff([], raw.decode('utf-8').splitlines(keepends=True),
                                         fromfile='/dev/null', tofile='b/' + target.lstrip('/')))
    (review / 'CANDIDATE_ADDITIONS.diff').write_text(''.join(diff), encoding='utf-8')
    audit = json.loads((HERE / 'evidence/SOURCE_AUDIT.json').read_bytes())
    originals = {row['role']: row for row in audit['sources'] if row.get('role')}
    reuse = [
        ('launch_original_remove.py', 'candidate/boot_recovery.py', 'same original client remove argv; durable systemd single job; fresh dynamic context'),
        ('read_original_remove_result.py', 'candidate/recovery_rules.py', 'exact original reply plus actual overlay/render/ZOCL teardown'),
        ('launch_original_load.py', 'candidate/boot_recovery.py', 'same original client load argv and original 4 firmware + 3 driver hashes'),
        ('read_original_load_result.py', 'candidate/recovery_rules.py', 'exact original reply; dynamic overlay suffix, exact VART, ZOCL parent/child/render pairing'),
        ('bench_identity_stop.py', 'candidate/boot_recovery.py', 'unchanged original program called by pinned SHA with ID_STOP_ONLY, never a new controller'),
    ]
    comparison = dict(schema='aura-boot-recovery-exact-source-comparison-1',
                      original_files_overwritten=0, original_default_firmware_changed=False,
                      original_cpu_adapters_copied_or_reimplemented=False,
                      original_boot_pid_hash_and_consumption_flags_reused=False,
                      algorithm_reuse=[dict(original=role, original_sha256=originals[role]['sha256'],
                                            original_snapshot=originals[role]['snapshot'], new_wrapper=wrapper,
                                            new_wrapper_sha256=sha((HERE / wrapper).read_bytes()), semantics=description)
                                       for role, wrapper, description in reuse],
                      unchanged_original_config_sources=[dict(path=row['remote_path'], before_sha256=row['sha256'], after_sha256=row['sha256'])
                                                         for row in audit['sources'] if row.get('remote_path')],
                      changed_runtime_fields_only=['UI board_business.face_readback', 'startup component_sha256[config/board_avatar_gtk.json]'],
                      retained_sources=['actual latest identity/GTK sources', 'original selected policy/model/gallery metadata',
                                        'all previous run-config source pins', 'original Native full Python/C/operator closure',
                                        'accepted axis controller/parameters and original GUI launcher'],
                      fresh_source_changes_require_new_capture=True, actual_device_comparison_performed=False,
                      unresolved_auxiliary_loader='Saved unit inventory lists generated dpu-auto-config; its current generated unit/init source and ordering require fresh review')
    comparison['runtime_history_reuse'] = dict(
        adapter_reference='candidate/cpu_adapters.reference.json', existing_adapter_copied=False,
        call_through='candidate/original_history_gate.py',
        cold='Original _sealed_source + unchanged CPU validate_chain against independently accepted ordered manifest',
        same_boot='Pinned genuine original complete result + unchanged validate_inputs/validate_current/validate_chain; caller verifies own ordered prestart state',
        original_Native_restore_commit_or_marker_implementation_changed=False)
    write_json(review / 'ORIGINAL_SOURCE_COMPARISON.json', comparison)
    manifest = dict(schema='aura-boot-recovery-candidate-manifest-1', client_date='2026-11-02', timezone='America/Los_Angeles',
                    generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    status='OFFLINE_REVIEWABLE_CANDIDATE_NOT_DEPLOYED', activation_supplied=False, ready_to_execute=False,
                    install_targets={path: dict(sha256=sha(raw), bytes=len(raw), must_be_absent_before_install=True)
                                     for path, raw in payload.items()},
                    revision=validation.get('revision'),
                    validation=dict(tests_run=validation['tests_run'], failed=0, errors=0, scope=validation.get('scope', 'Windows targeted public/synthetic metadata only'),
                                    baseline_validation=validation.get('baseline_validation'),
                                    previous_50_validation=validation.get('previous_50_validation'),
                                    previous_50_suite_rerun=validation.get('previous_50_suite_rerun', False),
                                    baseline_65_suite_rerun=validation.get('baseline_65_suite_rerun', False)),
                    independent_review_resolution=validation.get('change_receipt', 'review/INDEPENDENT_REVIEW_RESOLUTION.json'),
                    independent_approval_for_repaired_hashes=False,
                    source_comparison='review/ORIGINAL_SOURCE_COMPARISON.json', additions_diff='review/CANDIDATE_ADDITIONS.diff',
                    rollback_entry='candidate/manage_installation.py withdraw; optional guarded rollback-binding',
                    no_service_or_hardware_operations_performed=True, cold_boot_accepted=False)
    write_json(review / 'CANDIDATE_MANIFEST.json', manifest)
    common = [HERE / name for name in ('HANDOFF.txt', 'REVIEW.txt', 'ROLLBACK.txt', 'HISTORY_GATE_INTERFACE.txt', 'FRESH_HANDOFF.example.json')]
    common += [p for p in (HERE / 'candidate').rglob('*') if p.is_file()]
    common += [p for p in review.iterdir() if p.is_file()]
    common += [HERE / 'validation/LOCAL_VALIDATION.json', HERE / validation.get('log', 'validation/unittest_final.log')]
    if validation.get('baseline_validation'):
        common += [HERE / validation['baseline_validation']['path'], baseline_dir / 'unittest_final.log']
    common += [HERE / relative for relative in validation.get('supporting_evidence', [])]
    candidate_zip = zip_verified(HERE / 'DEPLOYMENT_CANDIDATE.zip', common)
    full = common + [p for p in (HERE / 'evidence').rglob('*') if p.is_file()]
    full += [p for p in (HERE / 'tests').glob('*.py')]
    full += [HERE / name for name in ('audit_saved_sources.py', 'reconcile_cpu_interface.py', 'record_targeted_revision.py',
                                     'seal_review_resolution.py', 'finalize_status.py', 'record_b01_revision7.py')]
    full += [Path(__file__).resolve()]
    rollback_zip = zip_verified(HERE / 'REVIEW_AND_ROLLBACK.zip', full)
    outputs = dict(schema='aura-boot-recovery-package-outputs-1', artifacts=[candidate_zip, rollback_zip],
                   archive_contents_exact_bytes_verified=True, activation_supplied=False,
                   ready_to_execute=False, deployed=False, cold_boot_accepted=False,
                   validation_receipt_sha256=sha((HERE / 'validation/LOCAL_VALIDATION.json').read_bytes()),
                   manifest_sha256=sha((review / 'CANDIDATE_MANIFEST.json').read_bytes()))
    write_json(HERE / 'PACKAGE_OUTPUTS.json', outputs)
    print(json.dumps(outputs, ensure_ascii=False))


if __name__ == '__main__':
    main()
