"""Read-only DPU identity configuration check; never claims a runtime self-test."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args()
    if not args.config.is_absolute():
        parser.error('--config must be an explicit absolute path')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    if config.get('schema_version') != 'aura-camera-identity-1':
        raise ValueError('Unknown camera identity configuration')
    config['database'] = str(Path(config['database']).expanduser())
    # Load only the pure-standard-library module by file path. This works on
    # an overlay without importing the running application's board package.
    spec = importlib.util.spec_from_file_location('aura_sface_configuration',
        str(ROOT/'board/identity/model_store.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print(json.dumps(module.check_artifact_configuration(config), sort_keys=True))


if __name__ == '__main__':main()
