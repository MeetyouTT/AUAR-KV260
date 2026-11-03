"""Read public exporter source and a single filtered motion-metadata packet."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
F = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
proc = Path('/proc/79866')
assert proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == '2265436'
assert hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest() == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
sources = {}
for relative in ('face_source.py', 'face-source-v17/face_timing.py',
                 'face-source-v17/stage_timing.py', 'face-source-v17/face_observation.py'):
    path = F / relative
    assert path.is_file() and not path.is_symlink() and path.resolve() == path
    raw = path.read_bytes()
    assert len(raw) < 100000
    sources[str(path)] = {'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8')}
c = http.client.HTTPConnection('127.0.0.1', 8790, timeout=2)
try:
    c.request('GET', '/v1/motion/face-stream?duration_ms=10000')
    response = c.getresponse()
    assert response.status == 200
    raw = response.readline(8193)
    assert len(raw) <= 8192 and raw.endswith(b'\n')
    packet = json.loads(raw)
    selected = {k: packet.get(k) for k in ('board_boot_id', 'frame_width', 'frame_height', 'mirror_horizontal', 'source_kind')}
    assert selected == {'board_boot_id': BOOT, 'frame_width': 640, 'frame_height': 480,
                        'mirror_horizontal': True, 'source_kind': 'actual'}
    timing = packet.get('detector_timing') or {}
    timing_types = {k: type(v).__name__ for k, v in timing.items()}
finally:
    c.close()
assert proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == '2265436'
print(json.dumps({'schema': 'aura-face-diagnostic-contract-readonly-1',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'board_monotonic_ms': int(time.monotonic()*1000),
    'sources': sources, 'filtered_current_packet': selected, 'detector_timing_value_types_only': timing_types,
    'camera_owner': {'pid': 79866, 'birth_ticks': '2265436', 'command_sha256': hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest()},
    'raw_packet_exported': False, 'image_or_box_or_identity_exported': False,
    'board_mutations': False, 'device_opened': False, 'controller_imported': False}, sort_keys=True))
