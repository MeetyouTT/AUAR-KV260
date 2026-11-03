"""Verify and run exactly the frozen nine public tests using Python stdlib only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def check_files(manifest):
    checked = 0
    for relative, pin in manifest['files'].items():
        parts = PurePosixPath(relative)
        if (parts.is_absolute() or not parts.parts or '..' in parts.parts
                or '\\' in relative or ':' in relative):
            raise ValueError('unsafe package-relative path')
        path = HERE
        for part in parts.parts:
            path = path / part
            if path.is_symlink():
                raise ValueError('symlink in pinned package input')
        if not path.is_file() or path.resolve().parent != (HERE / parts.parent).resolve():
            raise ValueError('missing or redirected package input: ' + relative)
        data = path.read_bytes()
        if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
            raise ValueError('package input differs from manifest: ' + relative)
        checked += 1
    return checked


def main():
    if sys.version_info < (3, 9):
        raise RuntimeError('Python 3.9 or newer is required')
    manifest_path = HERE / 'PACKAGE_MANIFEST.json'
    if manifest_path.is_symlink():
        raise ValueError('manifest must be a regular package file')
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data)
    if manifest['schema'] != 'aura.explicit-pause-resume-portable-validation.v1':
        raise ValueError('unexpected manifest schema')
    checked_before = check_files(manifest)
    if manifest['tests'] != 9 or len(manifest['support_components']) != 7:
        raise ValueError('unexpected validation scope')
    completed = subprocess.run(
        [sys.executable, '-I', '-B', str(HERE / 'test_public_methods_portable.py')],
        cwd=str(HERE), capture_output=True, text=True, timeout=60,
    )
    # Preserve unittest output and all failure diagnostics; no production module import.
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    checked_after = check_files(manifest)
    result_path = HERE / 'PORTABLE_TEST_RESULT.json'
    result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else {}
    passed = (completed.returncode == 0 and result.get('tests') == 9
              and result.get('failures') == 0 and result.get('errors') == 0
              and result.get('passed') is True
              and result.get('actual_controller_selector_and_production_wrapper_methods') is True
              and result.get('only_authored_temporary_selection_files') is True
              and result.get('actual_device_model_HTTP_service_private_database_or_grant_access') is False)
    receipt = {
        'schema': 'aura.explicit-pause-resume-portable-run-receipt.v1',
        'passed': passed,
        'python_version': platform.python_version(),
        'machine': platform.machine(),
        'manifest_sha256': hashlib.sha256(manifest_data).hexdigest(),
        'pinned_files_checked_before': checked_before,
        'pinned_files_checked_after': checked_after,
        'subprocess_exit_code': completed.returncode,
        'tests': result,
        'production_or_private_runtime_access': False,
        'deployment_performed': False,
    }
    (HERE / 'PORTABLE_RUN_RECEIPT.json').write_text(
        json.dumps(receipt, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=True))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
