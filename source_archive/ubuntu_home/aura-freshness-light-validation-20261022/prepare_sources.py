"""Copy pinned light observer/service tests for device-free verification."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
UPSTREAM = Path('/home/ghmd/aura-freshness-light-20261022')
BASELINE = SHARED / '2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py'
PINS = {
    'reference/face_targets.py': 'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0',
    'candidate/aura/board/identity/face_targets.py': '2f68d7ae75f67b2b1c67e7513296d6a6e907e02bcc0a5867d0f09c8fd1075577',
    'candidate/aura/board/identity/face_freshness_metrics.py': '206f565044a94a7f3f8369d25a1f98e587107b5f025d16f3c2cab6c19fe4a160',
    'tests/test_light.py': 'bab093ff51b75a8a6793b0b96993d460676d3bb54b24dcc4aa0e03d61dd3fa6f',
    'tests/test_service.py': '2a1a542a1a4e959f870ec946c436c7ae11ee2432496acb870b98aeeb8666e565',
}
EXPECTED_TESTS = 32


def prepare():
    if sys.flags.optimize:
        raise RuntimeError('Source preparation requires assertions enabled; remove -O/PYTHONOPTIMIZE')
    rows = {}
    for relative, expected in PINS.items():
        source = BASELINE if relative.startswith('reference/') else UPSTREAM / relative
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, relative
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
