"""Copy pinned light observer/service tests for device-free verification."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SHARED = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
UPSTREAM = Path('/home/ghmd/aura-yunet-recovery-20261023')
BASELINE = SHARED / '2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py'
PINS = {'reference/face_targets.py': 'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0', 'candidate/aura/board/identity/face_targets.py': 'dc2d494936eed900308a6f2cc7621b592a2fe9ef6a04387cf78ed5f83625d6b5', 'candidate/aura/board/identity/face_freshness_metrics.py': 'b7d6e9eb04ce73713b9a6f7a5c905d01bc6007841043623a3eb76bb6448edd2e', 'candidate/aura/board/vision/dpu_vision_runtime.py': 'e3b2d11140838fdf0eb548f8def033da5930ec46dfa72ae27f098c03e801c9d3', 'candidate/aura/board/vision/dpu_yunet.py': '23ea72f8380e7205fafb0d1b28b692a4780f1c9a51e221d04609843bbf0c309b', 'tests/test_light.py': 'f01a21f5d69d74e33fb2b32b5f995892ac92adaeef72f1486db8a8e7c443dfff', 'tests/test_service.py': '20bdef3b24e741889e9c3562c9ec9d34af06463bb3379966fab2fbfb66c34c9d'}
EXPECTED_TESTS = 35


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
