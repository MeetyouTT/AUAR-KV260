"""Build local candidate source pins from the parent's read-only snapshots."""
import hashlib
import json
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent


def make():
    source = HERE.parent/'resume_camera_pin'
    snapshot = json.loads((source/'actual_metadata_snapshot_v4.json').read_text(encoding='utf-8'))['files']
    more = json.loads((source/'native_lifecycle_more.json').read_text(encoding='utf-8'))
    pins = {}
    def add(name, digest):
        if name in pins and pins[name] != digest:
            raise ValueError('Snapshot pins conflict: '+name)
        pins[name] = digest
    for key, row in list(snapshot.items())+list(more.items()):
        if hashlib.sha256(row['content'].encode()).hexdigest() != row['sha256']:
            raise ValueError('Snapshot source bytes differ: '+key)
        if key not in ('old_config', 'current_config'):
            add(row['path'], row['sha256'])
    old = json.loads(snapshot['r17_deployment-manifest.json']['content'])
    for name, digest in old['pins'].items():add(name, digest)
    operator = json.loads(snapshot['operator_manifest']['content'])
    for name, digest in operator['files'].items():add(name, digest)
    meta = json.loads(snapshot['meta']['content'])
    for name, digest in meta.get('source_pins', {}).items():
        target = PurePosixPath(name)
        add(str(target if target.is_absolute() else PurePosixPath(meta['root'])/target), digest)
    root = HERE/'candidate'
    value = {
        'schema': 'aura-face-cadence-candidate-1',
        'candidate_sources': {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                              for name in ('entry.py', 'face_budget.py')},
        'inherited_pins': pins,
        'policy': {'inherited_period_ms': 100, 'target_period_ms': 200, 'optical_flow': True},
    }
    target = root/'candidate-manifest.json'
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    target.write_bytes(raw)
    return {'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'inherited_pins': len(pins),
            'candidate_sources': value['candidate_sources'], 'hardware_access': False}


if __name__ == '__main__':
    print(json.dumps(make(), ensure_ascii=False, indent=2))
