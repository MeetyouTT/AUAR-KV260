"""Create a NEW, disabled candidate configuration from the preserved Windows one.

No database, photo archive, runner, camera, device, or service is opened.
Thresholds remain null until separately calibrated for this INT8 model.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('fallback-config', 'model', 'manifest', 'database', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--enrollment-archive', type=Path)
    args = parser.parse_args()
    paths = [args.fallback_config, args.model, args.manifest, args.database, args.output]
    if any(not p.is_absolute() for p in paths):
        parser.error('All paths must be explicit absolute paths')
    spec = importlib.util.spec_from_file_location('aura_sface_configuration',
        str(ROOT/'board/identity/model_store.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import hashlib
    config = json.loads(args.fallback_config.read_text(encoding='utf-8'))
    config['model_id'] = module.MODEL_ID
    config['database'] = str(args.database)
    config['feature_backend'] = {'kind':'dpu_sface', 'model':str(args.model), 'manifest':str(args.manifest),
        'model_sha256':module.MODEL_SHA256,
        'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        'fallback_config':str(args.fallback_config),
        'max_source_age_ms':min(1000, config['result_ttl_ms'])}
    config['threshold'] = config['ambiguity_margin'] = None
    config['threshold_origin'] = 'INT8_FIELD_CALIBRATION_PENDING_DO_NOT_ENABLE'
    photos = config.get('enrollment_photos')
    if photos and photos.get('enabled'):
        if args.enrollment_archive is None or not args.enrollment_archive.is_absolute():
            parser.error('Preserving enabled photo policy requires a NEW version-named --enrollment-archive')
        photos['directory'] = str(args.enrollment_archive)
    check = module.check_artifact_configuration(config)
    raw = (json.dumps(config, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    # O_EXCL rejects existing files and symlinks, including the active config.
    descriptor = os.open(str(args.output), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as out:
        out.write(raw)
    check.update(candidate_config_created=True, configuration=str(args.output),
                 runtime_enabled=False, database_created=False, threshold_configured=False)
    print(json.dumps(check, sort_keys=True))


if __name__ == '__main__':main()
