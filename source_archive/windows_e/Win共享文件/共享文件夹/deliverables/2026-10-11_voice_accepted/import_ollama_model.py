"""Merge the saved model into another host's Ollama library without replacing files."""
import argparse
import json
import os
from pathlib import Path
import shutil
from verify_saved import digest, HERE, ROOT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models-dir', type=Path, default=Path(os.environ.get('OLLAMA_MODELS', str(Path.home() / '.ollama/models'))))
    args = parser.parse_args()
    target = args.models_dir.expanduser().resolve()
    prefix = 'aura/models/dialogue/ollama/'
    rows = [r for r in json.loads((HERE / 'model_files.json').read_text(encoding='utf-8'))['files'] if r['path'].startswith(prefix)]
    planned = []
    # Validate every source and destination before starting the merge.
    for row in rows:
        source = ROOT / row['path']
        dest = (target / row['path'][len(prefix):]).resolve()
        if not dest.is_relative_to(target):
            raise SystemExit('Destination outside model directory')
        if not source.is_file() or digest(source) != row['sha256']:
            raise SystemExit('Saved source hash mismatch: ' + str(source))
        if dest.exists() and (not dest.is_file() or digest(dest) != row['sha256']):
            raise SystemExit('Existing different file; merge stopped: ' + str(dest))
        planned.append((source, dest, row))
    for source, dest, row in planned:
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as src, dest.open('xb') as dst:
                shutil.copyfileobj(src, dst, 8 * 1024 * 1024)
        if digest(dest) != row['sha256']:
            raise SystemExit('Destination hash mismatch: ' + str(dest))
    print('PASS: qwen3:4b-instruct-2507-q4_K_M imported into ' + str(target))

if __name__ == '__main__':
    main()
