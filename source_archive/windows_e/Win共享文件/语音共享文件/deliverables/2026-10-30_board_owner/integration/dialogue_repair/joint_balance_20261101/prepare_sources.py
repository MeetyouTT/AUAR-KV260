"""Collect only local source bytes matching the latest fixed production manifest."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
BASE = PROJECT / 'deliverables/2026-10-31_visual_axis_maintenance/reviews/live_follow_test_20261101'
MANIFEST = BASE / 'package/original_direction_fix/new_manifest.json'
TARGETS = (
    'tools/board_avatar_gtk.py', 'tools/board_avatar_worker.py',
    'tools/board_camera_preview.py', 'tools/production_business_ui.py',
    'board/interaction/ui_services.py', 'board/interaction/ui_contract.py',
    'board/runtime/board_business.py', 'board/vision/local_preview.py',
    'tools/production_memory_presentation.py',
    'tests/framework/test_board_ui_services.py',
    'tests/framework/test_local_camera_preview.py',
)


def main():
    manifest_bytes = MANIFEST.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == '8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8'
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    command = ['rg', '--files', str(PROJECT / 'deliverables')]
    for rel in TARGETS:
        command += ['-g', Path(rel).name]
    paths = [Path(p) for p in subprocess.check_output(command, text=True, encoding='utf-8').splitlines()]
    index = {}
    for rel in TARGETS:
        expected = manifest['files']['runtime/aura/' + rel]
        source = next((p for p in paths if p.name == Path(rel).name
                       and p.stat().st_size == expected['bytes']
                       and hashlib.sha256(p.read_bytes()).hexdigest() == expected['sha256']), None)
        if source is None:
            raise ValueError('No exact local source: ' + rel)
        raw = source.read_bytes()
        destination = HERE / 'baseline' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == raw
        else:
            with destination.open('xb') as handle:
                handle.write(raw)
        index[rel] = dict(source=str(source), **expected)
    result = dict(schema='aura-joint-balance-source-index-1',
                  startup_sha256='226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15',
                  manifest_path=str(MANIFEST),
                  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  files=index, board_access=False, production_changed=False)
    raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    target = HERE / 'source_index.json'
    if target.exists():
        assert target.read_bytes() == raw
    else:
        with target.open('xb') as handle:
            handle.write(raw)
    print(json.dumps(dict(files=len(index), path=str(target), sha256=hashlib.sha256(raw).hexdigest())))


if __name__ == '__main__':
    main()
