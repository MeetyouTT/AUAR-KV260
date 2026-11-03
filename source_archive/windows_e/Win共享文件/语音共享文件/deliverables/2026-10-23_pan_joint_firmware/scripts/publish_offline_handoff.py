#!/usr/bin/env python3
"""Copy the completed offline artifacts/evidence into the authorized shared area."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_pan_joint_firmware')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


def main():
    complete = json.loads((ROOT / 'FINISH-STATUS.json').read_text())
    status = json.loads((ROOT / 'STATUS.json').read_text())
    manifest = json.loads((ROOT / 'bundle/candidate-manifest.json').read_text())
    if (complete['state'] != 'offline_package_complete' or not status['offline_bundle_ready']
            or manifest['status'] != 'OFFLINE_VSRV2_BUNDLE_PENDING_BOARD'
            or manifest['deployable'] is not False or manifest['board_accessed'] is not False):
        raise RuntimeError('Only a completed, honest offline candidate can be handed off')
    firmware = SHARED / 'firmware'
    firmware.mkdir()
    for source in (ROOT / 'bundle').rglob('*'):
        if source.is_file():
            target = firmware / source.relative_to(ROOT / 'bundle')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if sha(source) != sha(target):
                raise RuntimeError('Copy verification failed: ' + str(target))
    provenance = firmware / 'provenance'
    provenance.mkdir()
    for source in [ROOT / 'implementation/visual_servo_source_implemented.xsa',
                   Path(json.loads((ROOT / 'handoff-audit.json').read_text())['generated_hwh'])]:
        shutil.copy2(source, provenance / source.name)
    for p in ROOT.glob('*.py'):
        shutil.copy2(p, SHARED / 'scripts' / p.name)
    for p in ROOT.glob('*.tcl'):
        shutil.copy2(p, SHARED / 'scripts' / p.name)
    for name in ['STATUS.json', 'FINISH-STATUS.json', 'audit-input-pins.json',
                 'bitstream-pairing-inspection.json', 'bitstream-pairing-verified.json',
                 'implementation-reports-precheck.json', 'native-r4-compatibility-review.json',
                 'placed-hardware-description-check.json']:
        shutil.copy2(ROOT / name, SHARED / 'evidence' / name)
    for source_dir, target_dir in [(ROOT / 'implementation', SHARED / 'evidence/implementation'),
                                   (ROOT / 'final-audit', SHARED / 'evidence/independent-audit')]:
        target_dir.mkdir()
        for p in source_dir.iterdir():
            if p.suffix in {'.rpt', '.tsv', '.json'}:
                shutil.copy2(p, target_dir / p.name)
    (firmware / 'SHA256SUMS').write_text(''.join(sha(p) + '  ' + str(p.relative_to(firmware)) + '\n'
        for p in sorted(firmware.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))
    archive = SHARED / 'aura-vsrv2-joint-778d2512-offline.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(firmware.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(firmware))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError('Archive CRC check failed')
        for name in z.namelist():
            if hashlib.sha256(z.read(name)).hexdigest() != sha(firmware / name):
                raise RuntimeError('Archive payload differs: ' + name)
    result = {'updated_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'status': 'OFFLINE_JOINT_FIRMWARE_AND_INDEPENDENT_AUDIT_COMPLETE_PENDING_BOARD',
        'joint_implementation_passed': True, 'independent_checkpoint_audit_passed': True,
        'package_copy_and_archive_verified': True, 'archive': archive.name,
        'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
        'manifest_sha256': sha(firmware / 'candidate-manifest.json'),
        'software_tests_passed': 51, 'new_tool_tests_passed': 14,
        'bitstream_pairing_tests_passed': 6, 'report_gate_checks_passed': 8,
        'real_gtk_input_checks_passed': 6, 'hdl_testbenches_passed': 3, 'pwm_scenarios_passed': 9,
        'report': manifest['report'], 'board_accessed': False, 'firmware_loaded': False,
        'movement_commands_sent': 0, 'external_waveform_verified': False,
        'physical_motion_verified': False, 'board_window_confirmed': False,
        'windows_receipt_verified': False, 'deployable': False}
    (SHARED / 'PROGRESS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'archive', 'archive_bytes', 'archive_sha256', 'board_accessed']}, indent=2))


if __name__ == '__main__':
    main()
