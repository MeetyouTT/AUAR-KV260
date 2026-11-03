"""Pin the camera-feed bootstrap and no-IO live shadow files for UART transfer."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OPS = '/home/root/aura-native-live-20261024/ops/be72669aa53de735'
FILES = [
    ('shadow_runtime/native_entry_shadow.py', OPS + '/native_entry_pan_shadow.py'),
    ('shadow_runtime/shadow_follow.py', OPS + '/pan-follow-shadow-live/follow.py'),
    ('shadow_runtime/run_shadow.py', OPS + '/pan-follow-shadow-live/run_shadow.py'),
    ('config/pan_follow.shadow.json', OPS + '/pan-follow-shadow-live/config.json'),
]
rows = []
for source, destination in FILES:
    path = ROOT / source
    raw = path.read_bytes()
    rows.append({'source': str(path), 'source_rel': source,
                 'destination': destination, 'bytes': len(raw),
                 'sha256': hashlib.sha256(raw).hexdigest()})
manifest = {'schema': 'aura-pan-follow-shadow-transfer-1', 'ops_root': OPS,
            'release': 'pan-follow-shadow-live', 'files': rows}
manifest['manifest_sha256'] = hashlib.sha256(
    json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
(ROOT / 'shadow-bundle-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'manifest_sha256': manifest['manifest_sha256'],
                  'files': [{'source_rel': r['source_rel'], 'bytes': r['bytes'], 'sha256': r['sha256']}
                            for r in rows]}, sort_keys=True))
