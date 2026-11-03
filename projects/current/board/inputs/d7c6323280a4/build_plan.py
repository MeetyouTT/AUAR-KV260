"""Read/hash-only plan builder. It does not load any model or native library.

Run on the target's prepared files, or use a mirrored tree with target paths
before the final target-side hash check. It never controls production services.
"""
import argparse
import json
from pathlib import Path

from equivalence_benchmark import CASES, SCHEMA, SERVICE, pinned, sha256, validate_plan


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': sha256(path)}


def source_manifest(root, output):
    root = Path(root).resolve(strict=True)
    value = {'scope': 'complete Python source closure for exclusive synthetic equivalence only',
        'root': str(root), 'files': {str(p.relative_to(root)): sha256(p)
                                   for p in sorted(root.rglob('*.py'))}}
    with output.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2);handle.write('\n')
    return {'root': str(root), 'manifest': pin(output)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-root', required=True)
    parser.add_argument('--candidate-root', required=True)
    parser.add_argument('--bridge', required=True)
    parser.add_argument('--production-snapshot', required=True)
    parser.add_argument('--expected-boot-id', required=True)
    parser.add_argument('--yolo-owner-config', required=True,
        help='JSON containing only the original DpuYoloX constructor configuration')
    parser.add_argument('--optional-models', required=True,
        help='JSON list in yunet,sface order: task/model/manifest/source_ttl_ns, no identity DB')
    parser.add_argument('--new-output-directory', required=True)
    args = parser.parse_args(argv)
    yolo = json.loads(Path(args.yolo_owner_config).read_text())
    models = json.loads(Path(args.optional_models).read_text())
    for row in models:
        for name in ('model', 'manifest'):
            current = pin(row[name]);row[name] = current['path'];row[name + '_sha256'] = current['sha256']
    target = Path(args.new_output_directory).resolve()
    target.mkdir(mode=0o750, parents=False, exist_ok=False)
    legacy, candidate = Path(args.legacy_root).resolve(strict=True), Path(args.candidate_root).resolve(strict=True)
    artifacts = {'legacy_yolo': pin(legacy / 'board/vision/yolo_dpu.py'),
        'legacy_runtime': pin(legacy / 'board/vision/dpu_vision_runtime.py'),
        'candidate_binding': pin(candidate / 'board/vision/native_binding.py'),
        'candidate_protection': pin(candidate / 'board/vision/native_protection.py'),
        'bridge': pin(args.bridge), 'production_snapshot': pin(args.production_snapshot)}
    value = dict(schema=SCHEMA, purpose='isolated_model_equivalence', expected_boot_id=args.expected_boot_id,
        camera_service=SERVICE, cases=list(CASES), primary_period_ns=100_000_000,
        yolo_geometry=[640,480,1920], yolo_owner_config=yolo, models=models, artifacts=artifacts,
        source_sets={'legacy': source_manifest(legacy, target / 'legacy-python-sources.json'),
                     'candidate': source_manifest(candidate, target / 'candidate-python-sources.json')})
    validate_plan(value)
    for name, digest in [('model', 'model_sha256'), ('native_library', 'native_sha256')]:
        pinned({'path': yolo[name], 'sha256': yolo[digest]})
    pinned({'path': str(Path(yolo['model']).with_suffix('.prototxt')), 'sha256': yolo['model_config_sha256']})
    with (target / 'plan.json').open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2);handle.write('\n')
    print(json.dumps({'plan_created': str(target / 'plan.json'), 'models_loaded': False,
                      'candidate_library_loaded': False, 'services_changed': False}))


if __name__ == '__main__':main()
