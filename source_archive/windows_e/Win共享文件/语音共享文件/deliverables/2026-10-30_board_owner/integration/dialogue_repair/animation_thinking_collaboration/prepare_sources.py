"""Freeze only verified public source/configuration, never models or private data."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
INTEGRATION = REPAIR.parent
PROJECT = HERE.parents[4]
VERIFIED = REPAIR / 'feature_trigger_collaboration/runtime_v16'
MAPPING = REPAIR / 'paraformer_small_validation/v16_evidence/source_mapping.json'
NATIVE = PROJECT / 'deliverables/2026-10-30_yuki_native_validation/native_integration'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_once(source, destination, expected):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Unverified source: ' + str(source))
    if destination.exists() and destination.read_bytes() != raw:
        raise ValueError('Frozen destination already differs: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return dict(source=str(source), sha256=expected, bytes=len(raw))


def main():
    mapping = json.loads(MAPPING.read_text(encoding='utf-8'))
    rows = {}
    # This other window's immutable baseline is hash-checked, then copied into
    # our own directory. Its candidate/route files are neither read nor edited.
    for relative, digest in mapping['component_pins'].items():
        if relative.endswith('.py') or relative == 'config/character_profile.local.json':
            rows[relative] = copy_once(VERIFIED / relative, HERE / 'runtime_v16' / relative, digest)
    modified = ('tools/native_yuki.py', 'tools/formal_native_yuki.py', 'tools/formal_yuki.py')
    before = {}
    for relative in modified:
        source = HERE / 'runtime_v16' / relative
        digest = mapping['component_pins'][relative]
        before['aura/' + relative] = copy_once(source, HERE / 'before/aura' / relative, digest)
        copy_once(source, HERE / 'candidate/aura' / relative, digest)
    receipt = json.loads((INTEGRATION / 'appearance_native_framing/actual_build_receipt.json').read_text(encoding='utf-8'))
    native_inputs = {
        'yuki_host.cpp': (INTEGRATION / 'appearance_native_framing/yuki_host.cpp', receipt['patched_source_sha256']),
        'yuki_host.h': (NATIVE / 'host/yuki_host.h', receipt['header_pins']['host/yuki_host.h']),
    }
    for name, (source, digest) in native_inputs.items():
        before['native/' + name] = copy_once(source, HERE / 'before/native' / name, digest)
        copy_once(source, HERE / 'candidate/native' / name, digest)
    library = INTEGRATION / 'appearance_patch/root_overlay/aura/tools/libaura_yuki.so'
    before['aura/tools/libaura_yuki.so'] = copy_once(library,
        HERE / 'before/aura/tools/libaura_yuki.so', mapping['component_pins']['tools/libaura_yuki.so'])
    # Public formal selection contains renderer pins and must be resealed only
    # after the root owner builds the candidate library.
    relative = 'config/yuki_pair.formal.json'
    config = INTEGRATION / 'production_business_overlay/candidate/aura' / relative
    before['aura/' + relative] = copy_once(config, HERE / 'before/aura' / relative,
                                        mapping['component_pins'][relative])
    result = dict(schema='aura.animation-thinking-baseline.v1',
        root=mapping['root'], startup_sha256=mapping['startup_sha256'],
        source_manifest_sha256=mapping['source_manifest_sha256'], component_count=len(mapping['component_pins']),
        source_mapping_sha256=sha(MAPPING), source_mapping=str(MAPPING),
        native_build_receipt=str(INTEGRATION / 'appearance_native_framing/actual_build_receipt.json'),
        native_library_sha256=mapping['component_pins']['tools/libaura_yuki.so'],
        files=before, verified_python_sources=len(rows), source_only=True,
        private_data_read=False, device_access=False, production_modified=False)
    (HERE / 'SOURCE_BASELINE.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='FROZEN', python_sources=len(rows), before_files=len(before))))


if __name__ == '__main__':
    main()
