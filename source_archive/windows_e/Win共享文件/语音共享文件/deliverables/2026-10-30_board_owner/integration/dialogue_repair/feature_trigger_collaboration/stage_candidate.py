"""Create only isolated source copies, with a closed, hashed baseline."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
SOURCES = {
    'board/runtime/audio/board_dialogue_jobs.py': (
        'deliverables/2026-10-30_board_owner/integration/dialogue_repair/guard_session_candidate/after/board/runtime/audio/board_dialogue_jobs.py',
        '71fd1ac8e2ddb2e20eeb572063cc69e370e18f40af4a97fb65e2d8258bae45a0'),
    'board/runtime/visual_policy.py': ('aura/board/runtime/visual_policy.py',
        'efb730d82b812f4323e92c8d6fdf1e69ae9f8dbffab1a5c5db346a18d12b4dc9'),
    'tools/speaker_device.py': ('aura/tools/speaker_device.py',
        '73648e960ab28e16cce1e0676bd7981b5fc35c70bce9868b864e5c8881af4e00'),
    'common/voice_enrollment.py': ('aura/common/voice_enrollment.py', None),
    'tools/yuki_jobs_candidate.py': (
        'deliverables/2026-10-30_board_owner/integration/dialogue_repair/feature_trigger_collaboration/runtime_v16/tools/yuki_jobs_candidate.py',
        '6dd98c8a1be49f1c4a468ba10a585cbe3fbf36258d9e90d28c7423bac1f8093c'),
}


def main():
    rows = {}
    for relative, (source, expected) in SOURCES.items():
        path = PROJECT / source
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError('Local source changed: '+relative)
        rows[relative] = dict(source=str(path), sha256=digest, bytes=len(raw))
        for side in ('before', 'after'):
            destination = HERE/'candidate'/side/relative
            if destination.exists():
                if side == 'before' and destination.read_bytes() != raw:
                    raise ValueError('Frozen before source changed')
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
    (HERE/'candidate/SOURCE_BASELINE.json').write_text(
        json.dumps(dict(schema='aura.feature-source-baseline.v1',
                        reference='Every before-source verified against root v16 source_mapping.json',
                        files=rows), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'candidate_staged':len(rows),'production_changed':False}))


if __name__ == '__main__':
    main()
