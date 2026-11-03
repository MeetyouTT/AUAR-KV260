"""Assemble small, byte-checked offline sources. No device or model access."""
from pathlib import Path
import hashlib
import json
import shutil

OUT = Path(__file__).resolve().parents[1]
BUSINESS = OUT.parents[1]
SHARE = BUSINESS.parent
OWNER = BUSINESS / 'deliverables/2026-10-30_board_owner/integration'
EVIDENCE = OWNER / 'dialogue_repair/release_v23_memory_summary_candidate/memory_summary_evidence'
GUI = OWNER / 'dialogue_repair/feature_trigger_collaboration/joint_m03_identity_arm_v2/stage_v19_final_06e5/public_runtime_v19'
CONFIG = OWNER / 'production_business_overlay/fresh/aura'
WIDE = SHARE / '协作任务/2026-10-28_整机联动与舵机范围/offline_wide'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    pins = json.loads((EVIDENCE / 'source_mapping.json').read_text(encoding='utf-8'))
    entries = []

    def copy(source, relative, expected, basis):
        raw = source.read_bytes()
        if sha(raw) != expected:
            raise ValueError(f'Baseline changed: {source}')
        for directory in ('baseline', 'candidate'):
            target = OUT / directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise FileExistsError(target)
            target.write_bytes(raw)
        entries.append(dict(path=relative, source=str(source), sha256=expected,
                            bytes=len(raw), pin_basis=basis))

    wanted = ['board/__init__.py', 'tools/face_pan_controls.py',
              'tools/follow_process_cleanup.py', 'tools/pan_controls.py']
    wanted += [p.relative_to(GUI).as_posix() for p in (GUI / 'board/motion').glob('*.py')]
    for name in sorted(set(wanted)):
        copy(GUI / name, 'aura/' + name, pins['component_pins'][name], 'v23_component_pins')
    for name in ('pan_face.local.json', 'pan_manual.local.json', 'pan_direction.current.json'):
        copy(CONFIG / 'config' / name, 'aura/config/' + name,
             pins['component_pins']['config/' + name], 'v23_component_pins_historical_boot_config_not_permission')

    archive = json.loads((WIDE / 'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
    archive_pins = {x['path']: x['sha256'] for x in archive['files']}
    for source in sorted((WIDE / 'source/controller').rglob('*.py')):
        rel = source.relative_to(WIDE).as_posix()
        copy(source, 'controller/' + source.relative_to(WIDE / 'source/controller').as_posix(),
             archive_pins[rel], 'wide_archive_manifest_not_current_device_byte_check')

    metadata_path = OWNER / 'resume_camera_pin/actual_metadata_snapshot_v4.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    camera_entries = []
    for key, record in metadata['files'].items():
        if key.startswith('r17_') or key.startswith('actual_board/') or key in (
                'face_source', 'camera_wrapper', 'native_entry_pan_face_v5', 'native_entry_operator'):
            raw = record['content'].encode('utf-8')
            if sha(raw) != record['sha256']:
                raise ValueError(f'Embedded camera source changed: {key}')
            if not record['path'].endswith('.py'):
                continue
            target = OUT / 'audit_sources/camera' / (key.replace('/', '__') + '.txt')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            camera_entries.append(dict(key=key, path=record['path'], sha256=sha(raw),
                                       local_path=str(target), bytes=len(raw)))

    report = dict(schema='aura-visual-axis-offline-baseline-1',
                  production_startup_sha256=pins['startup_sha256'],
                  production_manifest_sha256=pins['source_manifest_sha256'],
                  mapping_sha256=sha((EVIDENCE / 'source_mapping.json').read_bytes()),
                  entries=entries, camera_source_entries=camera_entries,
                  camera_snapshot_sha256=sha(metadata_path.read_bytes()),
                  wide_archive_manifest_sha256=sha((WIDE / 'SOURCE_AND_EVIDENCE_MANIFEST.json').read_bytes()),
                  wide_live_controller_byte_match_verified=False,
                  production_sources_modified=False, camera_sources_modified=False,
                  hardware_accessed=False, model_weights_copied=False)
    evidence = OUT / 'evidence'
    evidence.mkdir(exist_ok=True)
    (evidence / 'baseline_manifest.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='BASELINE_ASSEMBLED', source_files=len(entries),
                          camera_audit_files=len(camera_entries),
                          physical_device_accessed=False)))


if __name__ == '__main__':
    main()
