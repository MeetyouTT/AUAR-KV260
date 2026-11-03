"""Validate this isolated candidate only; no project imports or live API calls."""
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sources = sorted([*HERE.glob('candidate/tools/*.py'), *HERE.glob('tests/test_*.py')])
for path in sources:
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
suite = unittest.defaultTestLoader.discover(str(HERE / 'tests'), pattern='test_*.py')
output = io.StringIO()
began = time.monotonic()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
(HERE / 'STARTUP_TESTS.log').write_text(output.getvalue(), encoding='utf-8')
metadata = dict(status='PASS' if result.wasSuccessful() else 'FAIL',
    checked_utc=datetime.now(timezone.utc).isoformat(),
    tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    skipped=len(result.skipped), elapsed_seconds=round(time.monotonic() - began, 4),
    platform=sys.platform, python=platform.python_version(),
    native_windows_file_lock_tests=sys.platform == 'win32',
    posix_backend_scope='mock call protocol only; no native Linux execution',
    real_ollama_calls=False, real_gpu_model_calls=False, board_calls=False,
    shared_business_source_changed=False,
    earlier_failure_record='STARTUP_TEST_FIRST_FAILURE.md')
(HERE / 'STARTUP_TEST_RESULTS.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
manifest = []
for path in sources + [HERE / 'STARTUP_VRAM_UNLOAD.md', HERE / 'STARTUP_TESTS.log', HERE / 'STARTUP_TEST_RESULTS.json', Path(__file__).resolve()]:
    data = path.read_bytes()
    manifest.append(dict(path=path.relative_to(HERE).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
(HERE / 'STARTUP_SOURCE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(metadata, ensure_ascii=False))
raise SystemExit(0 if result.wasSuccessful() else 1)
