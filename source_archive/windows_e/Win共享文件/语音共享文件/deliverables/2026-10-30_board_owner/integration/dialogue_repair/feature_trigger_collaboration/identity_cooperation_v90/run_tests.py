"""Local public-fixture tests against the exact saved v90 Python/config pins."""
from pathlib import Path
import hashlib
import importlib
import json
import sys

D = Path(__file__).resolve().parent
H = D.parent
BASE = H / 'candidate_m03_v90_stage/public_runtime_v90'
MAPPING = H / 'candidate_m03_v90_stage/source_mapping.v90.json'
PROJECT = H.parents[4]
assert hashlib.sha256(MAPPING.read_bytes()).hexdigest() == 'df6b26927ad60d6d3513429c697d70bd15c84cfdca6d16c5527e9992cb7b04e2'
mapping = json.loads(MAPPING.read_bytes())
configs = {'config/character_profile.local.json', 'config/persona.xuefei.candidate.json',
           'config/yuki_pair.formal.json', 'config/yuki_accepted_prompt.baseline.txt'}
pins = {p: s for p, s in mapping['component_pins'].items() if p.endswith('.py') or p in configs}
assert len(pins) == 343
for relative, digest in pins.items():
    path = BASE / relative
    assert not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
baseline = '--baseline' in sys.argv
with_m03 = '--with-m03' in sys.argv
if baseline:
    sys.argv.remove('--baseline')
if with_m03:
    sys.argv.remove('--with-m03')
    assert not baseline
sys.path.insert(0, str(BASE))
sys.path.insert(0, r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
for name in ('common', 'board', 'board.runtime', 'tools'):
    package = importlib.import_module(name)
    package.__path__ = [str(BASE / name.replace('.', '/'))]
if not baseline:
    candidate = D / 'after'
    manifest = json.loads((D / 'SOURCE_MANIFEST.json').read_bytes())
    for relative, row in manifest['files'].items():
        assert row['before_sha256'] == pins[relative]
        assert hashlib.sha256((candidate / relative).read_bytes()).hexdigest() == row['sha256']
    for name in ('board.runtime', 'tools'):
        package = importlib.import_module(name)
        package.__path__ = [str(candidate / name.replace('.', '/'))] + list(package.__path__)
    if with_m03:
        merged = D / 'combined_with_frozen_M03/board/runtime/board_business.py'
        proof = json.loads((D / 'MERGE_PROOF.json').read_bytes())
        assert hashlib.sha256(merged.read_bytes()).hexdigest() == proof['combined_business_sha256']
        m03 = H / 'candidate_m03_v90_stage/after'
        frozen = json.loads((H / 'candidate_m03_v90_stage/SOURCE_MANIFEST.json').read_bytes())
        for rel, row in frozen['files'].items():
            assert hashlib.sha256((m03 / rel).read_bytes()).hexdigest() == row['sha256']
        import board.runtime, tools
        board.runtime.__path__ = [str(merged.parent), str(candidate/'board/runtime'),
            str(m03/'board/runtime'), str(BASE/'board/runtime')]
        tools.__path__ = [str(candidate/'tools'), str(m03/'tools'), str(BASE/'tools')]
for name in ('board.runtime.board_business','board.runtime.board_speaker_business','tools.provisional_voice'):
    importlib.import_module(name)
for name in ('tests', 'tests.framework'):
    package = importlib.import_module(name)
    package.__path__ = [str(PROJECT / 'aura' / name.replace('.', '/'))] + list(package.__path__)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
