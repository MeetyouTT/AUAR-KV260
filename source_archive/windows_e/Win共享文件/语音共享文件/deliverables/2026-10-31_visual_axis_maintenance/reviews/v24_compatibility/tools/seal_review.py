"""Seal local compatibility evidence and the three-source R2 review payload."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import zipfile

REVIEW = Path(__file__).resolve().parents[1]
TASK = REVIEW.parents[1]
BUSINESS = TASK.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    compatibility = read(REVIEW / 'evidence/v24_before_pin_check.json')
    preserved = read(REVIEW / 'evidence/r1_preserved.json')
    r1 = read(TASK / 'review_bundle/candidate_manifest.json')
    assert sha(TASK / 'review_bundle/candidate_manifest.json') == preserved['r1_manifest_sha256']
    assert sha(TASK / 'evidence/after_fix_safety_final.json') == preserved['r1_test_result_sha256']
    before = read(REVIEW / 'evidence/r1_dialog_witness.json')
    after = read(REVIEW / 'evidence/r2_gui_targeted.json')
    assert before['tests'] == 8 and before['failures'] == 1 and not before['errors']
    assert after['tests'] == 8 and after['passed'] and not after['failures'] and not after['errors']
    clock_witness = read(REVIEW / 'evidence/r1_duplicate_clock_witness.json')
    controller = read(REVIEW / 'evidence/r2_controller_targeted.json')
    assert clock_witness['tests'] == 1 and clock_witness['failures'] == 1 and not clock_witness['errors']
    assert controller['tests'] == 41 and controller['passed'] and not controller['failures'] and not controller['errors']
    gui = REVIEW / 'candidate_r2/aura/tools/face_pan_controls.py'
    assert sha(gui) == after['tested_gui_sha256']
    carried = []
    for row in read(TASK / 'evidence/after_fix_safety_final.json')['source_pins']:
        if row['path'].startswith('controller/') or row['path'] in (
                'aura/board/__init__.py', 'aura/board/motion/__init__.py',
                'aura/board/motion/vsrv_driver.py'):
            assert sha(TASK / 'candidate' / row['path']) == row['sha256']
            carried.append(row)
    for row in r1['changed_files']:
        if row['path'].startswith('controller/'):
            expected = (controller['continuous_session_sha256'] if Path(row['path']).name == 'continuous_session.py'
                        else controller['session_target_lock_sha256'])
            assert sha(REVIEW / 'candidate_r2' / row['path']) == expected
    parsed = 0
    for directory in ('candidate_r2', 'tests', 'tools'):
        for path in (REVIEW / directory).rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            parsed += 1

    output = REVIEW / 'review_bundle_r2'
    output.mkdir(exist_ok=True)
    records, patch = [], []
    for row in r1['changed_files']:
        rel = row['path']
        original = TASK / 'baseline' / rel
        target = REVIEW / 'candidate_r2' / rel
        old = original.read_text(encoding='utf-8').splitlines(keepends=True) if original.exists() else []
        patch.extend(difflib.unified_diff(old, target.read_text(encoding='utf-8').splitlines(keepends=True),
            fromfile='a/' + rel if original.exists() else '/dev/null', tofile='b/' + rel))
        records.append(dict(path=rel, before_sha256=row['before_sha256'],
            r1_sha256=row['after_sha256'], r2_sha256=sha(target), bytes=target.stat().st_size))
    patch_path = output / 'visual_axis_r2.patch'
    patch_path.write_text(''.join(patch), encoding='utf-8')
    zip_path = output / 'visual_axis_r2_sources.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for row in records:
            info = zipfile.ZipInfo(row['path'], date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (REVIEW / 'candidate_r2' / row['path']).read_bytes())
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        for row in records:
            assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['r2_sha256']

    chain = read(REVIEW / 'evidence/controller_manifest_chain.json')
    replace = {Path(x['path']).name: x for x in records if x['path'].startswith('controller/')}
    entries = []
    for row in chain['entries']:
        item = dict(relative_path=row['relative_path'], before_sha256=row['expected_sha256'],
            proposed_sha256=row['expected_sha256'], action='PRESERVE_EXACT_BYTES',
            board_current_bytes_match=None)
        if item['relative_path'] in replace:
            item.update(proposed_sha256=replace[item['relative_path']]['r2_sha256'], action='REPLACE_IN_NEW_RELEASE')
        entries.append(item)
    new = replace['session_target_lock.py']
    entries.append(dict(relative_path='session_target_lock.py', before_sha256=None,
        proposed_sha256=new['r2_sha256'], action='ADD_TO_NEW_RELEASE', board_current_bytes_match=None))
    assert len(entries) == 26
    save(REVIEW / 'controller_release_plan.json', dict(
        schema='aura-controller-release-inventory-review-1', status='PLAN_NOT_RELEASE_MANIFEST',
        is_motion_permit=False, deployable=False, existing_manifest_sha256=chain['controller_manifest_sha256'],
        existing_release_root='/home/root/aura-pan-wide-20261028/control-10282601',
        proposed_release_root=None, existing_files=25, proposed_files=26, entries=entries,
        new_destination_root_and_full_manifest_must_be_selected_by_main=True,
        external_roots=['FIRMWARE_RELEASE_RETURNED_BY_VALIDATED_CONTEXT', 'APP_ROOT_FROM_FACE_CONFIG'],
        frozen_manifest_modified=False))
    manifest = dict(schema='aura-visual-axis-r2-v24-review-1',
        status='R2_LOCAL_REVIEW_READY_NOT_DEPLOYED', deployable=False,
        v24_startup_sha256=compatibility['startup_sha256'],
        v24_mapping_sha256=compatibility['mapping_sha256'],
        v24_before_gui_pins_verified=23, referenced_controller_python_pins_verified=22,
        current_board_controller_bytes_verified=False, current_firmware_vart_reference_verified=False,
        changed_files=records,
        changed_from_r1=['aura/tools/face_pan_controls.py', 'controller/continuous_session.py'],
        r1_test_run_preserved=46,
        current_gui_tests=8, current_controller_tests=41, combined_distinct_coverage=49,
        test_execution_groups=2, single_whole_suite_run_claimed=False,
        rerun_reason='New GUI dialog and duplicate-clock fixes, not the unrelated v24 memory component',
        preserved_dependency_pins=carried,
        current_gui_result_sha256=sha(REVIEW / 'evidence/r2_gui_targeted.json'),
        current_controller_result_sha256=sha(REVIEW / 'evidence/r2_controller_targeted.json'),
        syntax_checked_files=parsed, patch_sha256=sha(patch_path), zip_sha256=sha(zip_path),
        artifact_scope='three Python sources, no configuration, installer, binary library, firmware or model',
        production_source_modified=False, camera_or_memory_source_modified=False,
        ssh_uart_network_mmio_or_motion=False,
        face_identity_threshold_changed=False, biological_identity_or_profile_authorization_added=False)
    save(output / 'candidate_manifest_r2.json', manifest)
    save(REVIEW / 'evidence/seal_result.json', dict(status=manifest['status'],
        source_files=3, gui_tests_passed=8, controller_tests_passed=41,
        referenced_controller_files=25, proposed_controller_files=26,
        manifest_sha256=sha(output / 'candidate_manifest_r2.json'), zip_bytes=zip_path.stat().st_size,
        deployable=False, hardware_accessed=False))
    print(json.dumps(dict(status=manifest['status'], source_files=3, gui_tests=8,
        controller_tests=41, syntax_checked_files=parsed, zip_bytes=zip_path.stat().st_size)))


if __name__ == '__main__':
    main()
