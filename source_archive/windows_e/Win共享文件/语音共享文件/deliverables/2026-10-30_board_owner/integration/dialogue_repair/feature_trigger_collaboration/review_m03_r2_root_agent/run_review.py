"""Independent local review runner. Uses only public temporary Store fixtures."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
FEATURE = HERE.parent
REPAIR = FEATURE.parent
PROJECT = FEATURE.parents[4]
BASE = FEATURE / 'board_integration_v17/local_runtime_v17'
CANDIDATE = FEATURE / 'candidate_m03_r2'
sys.dont_write_bytecode = True
sys.path[:0] = [str(BASE), str(PROJECT / 'aura')]
sys.path.insert(0, r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads((CANDIDATE / 'SOURCE_MANIFEST.json').read_bytes())
sources = {}
for relative, expected in manifest['files'].items():
    path = CANDIDATE / 'after' / relative
    assert digest(path) == expected['sha256'], relative
    assert len(path.read_bytes()) == expected['bytes'], relative
    ast.parse(path.read_text(encoding='utf-8'), feature_version=(3, 9))
    sources[relative] = {'path': str(path), 'sha256': digest(path)}

test_paths = [
    FEATURE / 'review_m03_win_inference/test_delete_boundaries.py',
    CANDIDATE / 'tests/test_r2_guards_and_presentation.py',
    CANDIDATE / 'tests/test_legacy_m03_adapted.py',
    HERE / 'test_independent_boundaries.py',
]
assert digest(test_paths[0]) == '7528a035ae301b3bf0d3bb0747cb52c322f82b5a1c236102ba5d47915e0c008b'
test_pins = {str(path): digest(path) for path in test_paths}

overlays = {
    'common': [FEATURE / 'candidate_h01/after/common'],
    'board.runtime': [
        CANDIDATE / 'after/board/runtime',
        FEATURE / 'candidate_h01/after/board/runtime',
        FEATURE / 'candidate_speaker_close/after/board/runtime',
        REPAIR / 'memory_observation_candidate_r2/after/board/runtime',
    ],
    'tools': [CANDIDATE / 'after/tools'],
}
for name, directories in overlays.items():
    package = importlib.import_module(name)
    package.__path__ = [str(path) for path in directories] + list(package.__path__)
for name in ('tests', 'tests.framework'):
    package = importlib.import_module(name)
    package.__path__ = [str(PROJECT / 'aura' / name.replace('.', '/'))] + list(package.__path__)

module_names = [
    'common.board_memory',
    'board.runtime.board_dialogue',
    'board.runtime.board_memory_policy',
    'board.runtime.board_speaker_business',
    'board.runtime.history_delete',
    'board.runtime.board_business',
    'tools.production_memory_presentation',
]
loaded = {}
for name in module_names:
    module = importlib.import_module(name)
    path = Path(module.__file__)
    loaded[name] = {'path': str(path), 'sha256': digest(path)}

import pytest

result = pytest.main([
    '-q', '-p', 'no:cacheprovider',
    '--junitxml=' + str(HERE / 'INDEPENDENT.xml'),
    *map(str, test_paths),
])
assert all(digest(Path(path)) == sha for path, sha in test_pins.items())
assert all(digest(Path(value['path'])) == value['sha256'] for value in sources.values())
proof = {
    'status': 'PASS' if result == 0 else 'FAIL',
    'pytest_exit_code': int(result),
    'candidate_source_manifest_sha256': digest(CANDIDATE / 'SOURCE_MANIFEST.json'),
    'candidate_sources': sources,
    'loaded_modules': loaded,
    'test_pins': test_pins,
    'original_tests_and_candidates_modified': False,
    'models_devices_network_or_private_stores_accessed': False,
}
(HERE / 'SOURCE_PROOF.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
raise SystemExit(result)
