"""Stage only public production-pinned Python sources for synthetic tests."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
PROJECT = OUT.parents[1]
BASELINE = OUT/'identity_dialogue_collaboration/baseline'
RUNTIME = HERE/'runtime_v24'
SNAPSHOT = HERE.parent/'MEMORY_AND_SOURCE_CURRENT.json'
receipt = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
production = receipt['board_result']['component_sha256']
overrides = {
    'common/board_memory.py': PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/memory_source_cooldown_v25_candidate/before/common/board_memory.py',
    'board/runtime/board_memory_policy.py': PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/memory_negation_v24_candidate_r2/after/board/runtime/board_memory_policy.py',
    'config/character_profile.local.json': PROJECT/'aura/config/character_profile.local.json',
}
require_pins = {
    'common/board_memory.py': '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905',
    'board/runtime/board_memory_policy.py': 'd6e459f913a6c3d9827e0d90322cb9a2fb17ada87144b853dfdf02ed300f36c6',
    'common/board_memory_backoff.py': '9710c079fc589eae8f2eb26fba7f0dd80038b66736b3e45e000a98904716ce82',
}
assert len(production) == 380
assert all(production[key] == value for key, value in require_pins.items())
assert not RUNTIME.exists(), 'Keep each staged source closure immutable'
entries = {}

def add(relative):
    if relative in entries:
        return
    if relative not in production:
        raise RuntimeError('Source lacks a current production component pin: ' + relative)
    origin = overrides.get(relative, BASELINE/relative)
    content = origin.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    assert digest == production[relative], 'Local source differs from current production: ' + relative
    entries[relative] = {'source': str(origin), 'sha256': digest, 'bytes': len(content)}
    target = RUNTIME/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    if target.suffix != '.py':
        return
    package = '.'.join(Path(relative).parts[:-1])
    for i in range(1, len(Path(relative).parts)):
        parent = Path(*Path(relative).parts[:i])/'__init__.py'
        if parent.as_posix() in production:
            add(parent.as_posix())
    for node in ast.walk(ast.parse(content.decode('utf-8'))):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ''
            if node.level:
                name = importlib.util.resolve_name('.'*node.level + name, package)
            names = [name]
        for name in names:
            if name.split('.')[0] not in ('common', 'board'):
                continue
            candidate = name.replace('.', '/') + '.py'
            init = name.replace('.', '/') + '/__init__.py'
            if candidate in production:
                add(candidate)
            elif init in production:
                add(init)
            else:
                raise RuntimeError('Unresolved project dependency: ' + name)

for entry in ('common/board_memory.py', 'common/board_memory_backoff.py',
              'common/profile_access.py', 'board/runtime/board_memory_policy.py',
              'config/character_profile.local.json'):
    add(entry)

tests = {}
for name in ('test_board_memory.py', 'test_board_memory_search_clear.py'):
    original = PROJECT/'aura/tests/framework'/name
    content = original.read_bytes()
    target = RUNTIME/'tests/framework'/name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    tests[name] = {'source': str(original), 'sha256': hashlib.sha256(content).hexdigest()}
for package in ('tests', 'tests/framework'):
    (RUNTIME/package/'__init__.py').write_bytes(b'')

manifest = {
    'schema': 'aura-synthetic-memory-current-source-closure-1',
    'actual_production_metadata': str(SNAPSHOT),
    'actual_production_metadata_sha256': hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
    'component_count': 380, 'staged_component_count': len(entries),
    'all_staged_sources_match_current_production': True,
    'sources': entries, 'original_test_sources': tests,
    'tests_are_synthetic_not_current_production_components': True,
    'board_accessed': False, 'real_database_opened': False,
    'production_files_modified': False,
}
(HERE/'SOURCE_CLOSURE.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'staged_components': len(entries), 'all_current_production_pins_match': True}))
