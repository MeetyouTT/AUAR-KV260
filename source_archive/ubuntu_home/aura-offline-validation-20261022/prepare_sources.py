"""Copy only frozen, reviewed Python sources for device-free verification."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
UPSTREAM = SHARED / '2026-10-22_yunet_freshness_metrics'
BASELINE = SHARED / '2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py'
PINS = {
    'reference/face_targets.py': 'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0',
    'candidate/aura/board/identity/face_targets.py': '2f68d7ae75f67b2b1c67e7513296d6a6e907e02bcc0a5867d0f09c8fd1075577',
    'candidate/aura/board/identity/face_freshness_metrics.py': '13cea34f2692fd572ba2e81aaaac1577ab065f2c452cb449593de473a659b5b0',
    'tests/test_freshness_metrics.py': '9479675474d10ea067142f5d61997eeb3ddb17794ad4e386aad4a1b51b55aebc',
}


def prepare():
    if sys.flags.optimize:
        raise RuntimeError('Source preparation requires assertions enabled; remove -O/PYTHONOPTIMIZE')
    manifest = json.loads((UPSTREAM / 'manifest.json').read_text())
    assert manifest['validation']['tests_passed'] == 23
    rows = {}
    for relative, expected in PINS.items():
        source = BASELINE if relative.startswith('reference/') else UPSTREAM / relative
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, relative
        if not relative.startswith('reference/'):
            assert manifest['files'][relative]['sha256'] == expected
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == raw, 'Refuse to overwrite different local source'
        else:
            target.write_bytes(raw)
        rows[relative] = {'sha256': expected, 'bytes': len(raw), 'source': str(source)}
    (ROOT / 'sources.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps({'copied_or_verified_files': len(rows), 'device_operations': 0}))


if __name__ == '__main__':
    prepare()
