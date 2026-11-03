"""Run isolated adapter tests and verify the original forty source snapshots."""
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
sys.dont_write_bytecode = True
sources = sorted([*HERE.glob('candidate/tools/*.py'), *HERE.glob('tests/test*.py')])
for path in sources: ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
base_manifest = json.loads((RESEARCH / 'STARTUP_SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for row in base_manifest:
    if row['path'].startswith(('candidate/', 'tests/')):
        current = hashlib.sha256((RESEARCH / row['path']).read_bytes()).hexdigest()
        if current != row['sha256']: raise RuntimeError('Original forty-test source changed: ' + row['path'])
base = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(RESEARCH / 'tests'), '-p', 'test_*.py', '-q'],
    cwd=RESEARCH, capture_output=True, timeout=30, text=True, encoding='utf-8', errors='replace',
    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
(HERE / 'BASE40.log').write_text(base.stdout + base.stderr, encoding='utf-8')
stream = io.StringIO()
suite = unittest.defaultTestLoader.discover(str(HERE / 'tests'), pattern='test*.py')
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
(HERE / 'TESTS.log').write_text(stream.getvalue(), encoding='utf-8')
metadata = dict(status='PASS' if base.returncode == 0 and result.wasSuccessful() else 'FAIL',
    checked_utc=datetime.now(timezone.utc).isoformat(), adapter_tests=result.testsRun,
    adapter_failures=len(result.failures), adapter_errors=len(result.errors),
    base40_returncode=base.returncode, base40_sources_unchanged=True,
    real_model_calls=False, real_device_queries=False, automatic_unloading=False,
    production_or_parent_source_changed=False)
(HERE / 'VALIDATION.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
dependencies = [RESEARCH / 'candidate/tools/service_instance_lock.py',
    RESEARCH.parent / '2026-10-29_gpu_coordination/candidate/common/gpu_coordination.py']
manifest = dict(files=[], dependencies=[])
for path in sources + [HERE / 'README.md', Path(__file__).resolve(), HERE / 'VALIDATION.json', HERE / 'TESTS.log', HERE / 'BASE40.log']:
    data = path.read_bytes()
    manifest['files'].append(dict(path=path.relative_to(HERE).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
for path in dependencies:
    data = path.read_bytes()
    manifest['dependencies'].append(dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
(HERE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(metadata))
raise SystemExit(0 if metadata['status'] == 'PASS' else 1)
