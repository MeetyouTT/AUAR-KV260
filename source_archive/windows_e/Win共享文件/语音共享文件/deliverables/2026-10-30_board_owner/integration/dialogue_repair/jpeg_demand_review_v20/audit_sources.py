"""Read pinned local source files only; no device, model, HTTP or production writes."""
import hashlib
import json
from pathlib import Path


PROJECT = Path(r'E:\Win共享文件\语音共享文件')
REPAIR = PROJECT / 'deliverables/2026-10-30_board_owner/integration/dialogue_repair'
OUTPUT = Path(__file__).resolve().parent
MAPPING = REPAIR / 'release_v20_identity_history_candidate/identity_history_evidence/source_mapping.json'
ROOTS = [
    REPAIR / 'release_v20_identity_history_candidate/payload',
    REPAIR / 'release_v19_stability_candidate/payload',
    REPAIR / 'feature_trigger_collaboration/joint_m03_identity_arm_v2/stage_v19_final_06e5/public_runtime_v19',
    REPAIR / 'feature_trigger_collaboration/board_integration_v17/local_runtime_v17',
    PROJECT / 'deliverables/2026-10-30_board_owner/integration/production_business_overlay/fresh/aura',
    PROJECT / 'aura',
]
TERMS = [
    '/v1/ui/preview.jpg', '/v1/ui/identity-face.png', 'visual_frame(',
    'current_frame(', 'preview_transport', 'raw_preview', 'publish_preview(',
    'RawFrameReader', 'CameraPreviewWorker', 'preview_buffers', 'preview_frames',
]
CODE_SUFFIXES = {'.py', '.sh', '.ps1', '.js', '.ts', '.html', '.cpp', '.cc', '.h', '.c'}


def main():
    mapping_bytes = MAPPING.read_bytes()
    mapping = json.loads(mapping_bytes)
    records, missing, matches = [], [], []
    for relative, expected in sorted(mapping['component_pins'].items()):
        if Path(relative).suffix not in CODE_SUFFIXES:
            continue
        found = None
        for root in ROOTS:
            path = root / relative
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
                found = path
                break
        if found is None:
            missing.append(relative)
            continue
        records.append({'component': relative, 'path': str(found), 'sha256': expected})
        lines = found.read_text(encoding='utf-8-sig').splitlines()
        for number, line in enumerate(lines, 1):
            terms = [term for term in TERMS if term in line]
            if terms:
                matches.append({'component': relative, 'line': number, 'terms': terms, 'source': line.strip()})
    result = {
        'schema': 'aura.jpeg-consumers-pinned-audit.v1',
        'scope': 'All code-suffix components in the saved v20 source mapping; not arbitrary external clients or live sockets',
        'source_mapping': str(MAPPING),
        'source_mapping_sha256': hashlib.sha256(mapping_bytes).hexdigest(),
        'startup_sha256': mapping['startup_sha256'],
        'components_total': len(mapping['component_pins']),
        'code_components_found': len(records),
        'missing_code_components': missing,
        'files': records,
        'matches': matches,
        'device_accessed': False,
        'production_modified': False,
        'model_data_read_or_copied': False,
        'private_images_or_transcripts_read': False,
    }
    (OUTPUT / 'SOURCE_AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('startup_sha256', 'components_total', 'code_components_found', 'missing_code_components')}))
    for row in matches:
        if any(term in row['terms'] for term in ('/v1/ui/preview.jpg', 'visual_frame(', 'current_frame(')):
            print(json.dumps(row))


if __name__ == '__main__':
    main()
