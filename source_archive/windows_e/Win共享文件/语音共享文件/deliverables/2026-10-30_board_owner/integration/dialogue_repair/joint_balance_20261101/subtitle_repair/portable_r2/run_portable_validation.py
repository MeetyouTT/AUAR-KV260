"""Same public regressions on Windows or ARM Linux; standard library only."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def main():
    report = dict(schema='aura-public-subtitle-portable-run-r2',
        sys_version=sys.version, version_info=list(sys.version_info[:3]),
        platform=platform.platform(), machine=platform.machine(),
        feature_based_python_minimum='3.8',
        minimum_basis=['dataclasses and future annotations (3.7)',
                       'AST Module type_ignores field (3.8)'],
        candidate_sha256='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2',
        tests={}, passed=False, device_model_database_constructed=False)
    print(json.dumps({key: report[key] for key in
        ['schema', 'sys_version', 'version_info', 'platform', 'machine']}, sort_keys=True), flush=True)
    target = HERE/'PORTABLE_RUN_RESULT.json'
    target.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    pins = json.loads((HERE/'SOURCE_PINS.json').read_text(encoding='utf-8'))
    for pin in pins['files'].values():
        assert hashlib.sha256((HERE/pin['public_fixture']).read_bytes()).hexdigest() == pin['sha256']
    for name in ['test_submit_lifecycle.py', 'test_preserved_projection.py']:
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE/name)], cwd=HERE)
        report['tests'][name] = dict(returncode=result.returncode)
        target.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        if result.returncode:
            return result.returncode
    report['passed'] = True
    target.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('PUBLIC_SUBTITLE_REGRESSIONS_PASS; no device/model/database construction')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
