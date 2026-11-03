"""Seal a three-file review payload. This tool cannot install or use devices."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUSINESS = ROOT.parents[1]
CHANGES = {'aura/tools/face_pan_controls.py', 'controller/continuous_session.py',
           'controller/session_target_lock.py'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    baseline = json.loads((ROOT / 'evidence/baseline_manifest.json').read_text(encoding='utf-8'))
    before = {row['path']: row for row in baseline['entries']}
    for rel, row in before.items():
        assert sha(ROOT / 'baseline' / rel) == row['sha256'], rel
        assert sha(Path(row['source'])) == row['sha256'], row['source']
    for row in baseline['camera_source_entries']:
        assert sha(Path(row['local_path'])) == row['sha256']
    candidates = {p.relative_to(ROOT / 'candidate').as_posix(): p
                  for p in (ROOT / 'candidate').rglob('*') if p.is_file()}
    changed = {rel for rel, path in candidates.items()
               if rel not in before or sha(path) != before[rel]['sha256']}
    assert changed == CHANGES, changed
    assert set(before).issubset(candidates)
    syntax_checked = 0
    for directory in ('candidate', 'tests', 'tools'):
        for path in (ROOT / directory).rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            syntax_checked += 1
    report = json.loads((ROOT / 'evidence/after_fix_safety_final.json').read_text(encoding='utf-8'))
    assert report['passed'] and report['tests'] == 46 and not report['failures'] and not report['errors']
    for row in report['source_pins']:
        assert sha(ROOT / 'candidate' / row['path']) == row['sha256']

    release = ROOT / 'review_bundle'
    release.mkdir(exist_ok=True)
    patch_lines = []
    changed_records = []
    for rel in sorted(CHANGES):
        old_path = ROOT / 'baseline' / rel
        new_path = ROOT / 'candidate' / rel
        old_lines = old_path.read_text(encoding='utf-8').splitlines(keepends=True) if old_path.exists() else []
        patch_lines.extend(difflib.unified_diff(old_lines,
            new_path.read_text(encoding='utf-8').splitlines(keepends=True),
            fromfile='a/' + rel if old_path.exists() else '/dev/null', tofile='b/' + rel))
        changed_records.append(dict(path=rel,
            before_sha256=before[rel]['sha256'] if rel in before else None,
            after_sha256=sha(new_path), bytes=new_path.stat().st_size))
    patch_path = release / 'visual_axis_candidate.patch'
    patch_path.write_text(''.join(patch_lines), encoding='utf-8')
    bundle_path = release / 'visual_axis_candidate_sources.zip'
    with zipfile.ZipFile(bundle_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in sorted(CHANGES):
            info = zipfile.ZipInfo(rel, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (ROOT / 'candidate' / rel).read_bytes())
    with zipfile.ZipFile(bundle_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == CHANGES
        for row in changed_records:
            assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['after_sha256']

    mapping_path = BUSINESS / ('deliverables/2026-10-30_board_owner/integration/dialogue_repair/'
        'release_v23_memory_summary_candidate/memory_summary_evidence/source_mapping.json')
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    audit_rels = ['board/vision/person_bytetrack.py', 'board/fusion/targets.py',
        'board/identity/live.py', 'board/identity/store.py', 'board/visual_timeline.py',
        'board/runtime/visual_memory.py', 'board/runtime/board_business.py',
        'common/speaker_visual.py', 'common/profile_access.py', 'common/identity_links.py']
    owner = BUSINESS / 'deliverables/2026-10-30_board_owner/integration'
    command = ['rg', '--files', str(owner)]
    for name in sorted({Path(rel).name for rel in audit_rels}):
        command += ['-g', name]
    audit_files = sorted(Path(p) for p in subprocess.check_output(command, encoding='utf-8').splitlines())
    audit_index = []
    for rel in audit_rels:
        expected = mapping['component_pins'][rel]
        source = next(p for p in audit_files if p.name == Path(rel).name and sha(p) == expected)
        target = ROOT / 'audit_sources/v23' / (rel + '.txt')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        audit_index.append(dict(component=rel, sha256=expected, source=str(source),
            local_path=str(target), pin_matches_v23=True))
    save(ROOT / 'evidence/code_audit_index.json', audit_index)
    identity_path = BUSINESS / ('deliverables/2026-10-30_board_owner/integration/'
        'production_business_overlay/fresh/aura/config/board_identity.json')
    identity = json.loads(identity_path.read_text(encoding='utf-8'))
    assert sha(identity_path) == mapping['component_pins']['config/board_identity.json']
    assert identity['threshold'] == .85
    old_identity = json.loads((BUSINESS / 'aura/config/board_identity.json').read_text(encoding='utf-8'))
    save(ROOT / 'evidence/threshold_audit.json', dict(
        v23_configuration_pin_matches=True, v23_public_threshold=identity['threshold'],
        v23_ambiguity_margin=identity['ambiguity_margin'],
        business_root_old_threshold=old_identity['threshold'],
        current_camera_threshold_live_verified=False,
        threshold_changed=False, source='local_saved_configuration_only'))
    snapshot = json.loads((BUSINESS / ('deliverables/2026-10-30_board_owner/integration/'
        'resume_camera_pin/actual_metadata_snapshot_v4.json')).read_text(encoding='utf-8'))
    preserved = [dict(path=rel, sha256=row['sha256']) for rel, row in sorted(before.items())
                 if rel not in CHANGES]
    manifest = dict(schema='aura-visual-axis-review-payload-1',
        status='OFFLINE_REVIEW_READY_NOT_DEPLOYED', deployable=False, installs_nothing=True,
        v23_startup_sha256=baseline['production_startup_sha256'],
        v23_mapping_sha256=baseline['mapping_sha256'],
        wide_archive_manifest_sha256=baseline['wide_archive_manifest_sha256'],
        wide_live_controller_source_match_verified=False,
        camera_audit_snapshot_boot=snapshot['boot'], camera_audit_snapshot_pid=snapshot['pid'],
        current_camera_source_match_verified=False,
        changed_files=changed_records, preserved_files=preserved,
        syntax_checked_files=syntax_checked, offline_tests=report['tests'],
        test_result_sha256=sha(ROOT / 'evidence/after_fix_safety_final.json'),
        patch_sha256=sha(patch_path), zip_sha256=sha(bundle_path),
        source_originals_unchanged=True, camera_sources_modified=False,
        identity_threshold_changed=False, identity_permission_code_in_payload=False,
        memory_source_in_payload=False, model_weights_in_payload=False,
        native_library_in_payload=False, firmware_in_payload=False,
        no_service_control_or_device_access=True,
        integration_requirements=[
            'Main window must compare current GUI source against the before SHA.',
            'Archived controller baseline must match actual wide controller source, or rebase and rerun offline tests.',
            'Create a new complete pinned controller release including session_target_lock.py; never rewrite a frozen manifest.',
            'Keep FPGA, native libraries, firmware/VART, image/anchor deadlines, lease/STOP, range and identity gates unchanged.',
            'Current boot, FDT, stopped reference, direction/mounting and paused-listening constraints require fresh main-window checks.',
            'This payload provides no physical movement permission or mechanical acceptance.'
        ])
    save(release / 'candidate_manifest.json', manifest)
    print(json.dumps(dict(status=manifest['status'], changed_files=len(CHANGES),
        preserved_files=len(preserved), syntax_checked_files=syntax_checked,
        tests=report['tests'], zip_bytes=bundle_path.stat().st_size, deployable=False)))


if __name__ == '__main__':
    main()
