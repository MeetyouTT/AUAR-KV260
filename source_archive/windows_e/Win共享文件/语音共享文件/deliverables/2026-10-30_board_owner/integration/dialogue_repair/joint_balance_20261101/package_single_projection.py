"""Freeze a small, source-only public test package for the device owner."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
FILES = (
    'baseline/tools/production_memory_presentation.py',
    'presentation_candidate/tools/production_memory_presentation.py',
    'prepare_presentation_candidate.py', 'test_single_projection.py',
    'benchmark_single_projection.py', 'presentation_candidate_manifest.json',
    'presentation_test_result.json', 'source_index.json',
)


def main():
    test = json.loads((HERE / 'presentation_test_result.json').read_text(encoding='utf-8'))
    assert test['passed'] is True and test['tests'] == 11 and not test['failures'] and not test['errors']
    rows = {}
    path = HERE / 'single_projection_public_validation.zip'
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            raw = (HERE / name).read_bytes()
            archive.writestr(name, raw)
            rows[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    result = dict(schema='aura-single-projection-public-package-1', status='FROZEN_OFFLINE_TEST_PACKAGE',
                  archive=str(path), bytes=path.stat().st_size,
                  sha256=hashlib.sha256(path.read_bytes()).hexdigest(), files=rows,
                  deployable=False, board_executed=False,
                  required_operator_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',
                  no_models_or_private_data_or_credentials=True)
    target = HERE / 'single_projection_package_manifest.json'
    with target.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(path=str(target), sha256=result['sha256'], bytes=result['bytes'])))


if __name__ == '__main__':
    main()
