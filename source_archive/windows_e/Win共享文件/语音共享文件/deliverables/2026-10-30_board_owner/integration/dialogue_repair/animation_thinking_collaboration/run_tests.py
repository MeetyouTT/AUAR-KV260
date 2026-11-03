"""Local, device-free unittest runner using a private verified source tree."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

HERE = Path(__file__).resolve().parent


def main():
    baseline = json.loads((HERE / 'SOURCE_BASELINE.json').read_text(encoding='utf-8'))
    mapping = json.loads(Path(baseline['source_mapping']).read_text(encoding='utf-8'))
    runtime = HERE / 'test_runtime'
    for path in (HERE / 'runtime_v16').rglob('*'):
        if not path.is_file() or path.suffix not in ('.py', '.json'):
            continue
        relative = path.relative_to(HERE / 'runtime_v16').as_posix()
        if hashlib.sha256(path.read_bytes()).hexdigest() != mapping['component_pins'][relative]:
            raise ValueError('Frozen baseline changed: ' + relative)
        destination = runtime / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    for path in (HERE / 'candidate/aura').rglob('*.py'):
        relative = path.relative_to(HERE / 'candidate/aura')
        destination = runtime / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    sys.path.insert(0, str(runtime))
    sys.dont_write_bytecode = True
    suite = unittest.defaultTestLoader.discover(str(HERE / 'tests'), pattern='test_*.py')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (HERE / 'TEST_LOG.txt').write_text(log.getvalue(), encoding='utf-8')
    print(log.getvalue())
    summary = dict(schema='aura.animation-thinking-tests.v1', tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        successful=result.wasSuccessful(), python=sys.executable, device_access=False,
        model_inference=False, microphone_opened=False, audio_device_opened=False,
        real_dialogue_or_pcm_collected=False, native_binary_executed=False,
        candidate_python_sha256={p.relative_to(HERE/'candidate').as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'candidate/aura').rglob('*.py'))})
    (HERE / 'TEST_RESULTS.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
