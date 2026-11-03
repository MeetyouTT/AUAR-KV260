"""Same public regressions on Windows or ARM Linux; standard library only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def main():
    pins = json.loads((HERE/'SOURCE_PINS.json').read_text(encoding='utf-8'))
    for pin in pins['files'].values():
        assert hashlib.sha256((HERE/pin['public_fixture']).read_bytes()).hexdigest() == pin['sha256']
    for name in ['test_submit_lifecycle.py', 'test_preserved_projection.py']:
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE/name)], cwd=HERE)
        if result.returncode:
            return result.returncode
    print('PUBLIC_SUBTITLE_REGRESSIONS_PASS; no device/model/database construction')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
