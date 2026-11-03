"""Copy pinned light observer/service tests for device-free verification."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
UPSTREAM = Path('/home/ghmd/aura-yunet-retry-light-20261022')
BASELINE = SHARED / '2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py'
PINS = {
    'reference/face_targets.py': 'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0',
    'candidate/aura/board/identity/face_targets.py': '407cc5ee9e20ef6f08647117cc94b6ed3a88cb277d74e393f31eea92dd8cd809',
    'candidate/aura/board/identity/face_freshness_metrics.py': '4fdc28ea3505864551c90ea252a1a12bccce21ab1a1ccbdc2edbbb2242a89596',
    'candidate/aura/board/vision/dpu_vision_runtime.py': 'e3b2d11140838fdf0eb548f8def033da5930ec46dfa72ae27f098c03e801c9d3',
    'candidate/aura/board/vision/dpu_yunet.py': '23ea72f8380e7205fafb0d1b28b692a4780f1c9a51e221d04609843bbf0c309b',
    'tests/test_light.py': 'bab093ff51b75a8a6793b0b96993d460676d3bb54b24dcc4aa0e03d61dd3fa6f',
    'tests/test_service.py': '20bdef3b24e741889e9c3562c9ec9d34af06463bb3379966fab2fbfb66c34c9d',
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
