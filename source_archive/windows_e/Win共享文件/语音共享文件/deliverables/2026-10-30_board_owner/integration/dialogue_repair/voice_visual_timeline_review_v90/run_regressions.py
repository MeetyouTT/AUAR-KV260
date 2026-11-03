"""Pinned local package overlay, public fixtures only."""
import hashlib
import importlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
FEATURE = REPAIR / 'feature_trigger_collaboration'
IDENTITY = FEATURE / 'identity_cooperation_v90'
M03 = FEATURE / 'candidate_m03_v90_stage'
BASE = M03 / 'public_runtime_v90'
PROJECT = REPAIR.parents[3]
mapping_path = M03 / 'source_mapping.v90.json'
assert hashlib.sha256(mapping_path.read_bytes()).hexdigest() == 'df6b26927ad60d6d3513429c697d70bd15c84cfdca6d16c5527e9992cb7b04e2'
mapping = json.loads(mapping_path.read_bytes())
v19_path = REPAIR / 'release_v19_stability_candidate/stability_evidence/source_mapping.json'
assert hashlib.sha256(v19_path.read_bytes()).hexdigest() == 'ef8db220fde3b70a62ff1ff7cf2e9471a199a6d43b9234a18f8701eff58448f7'
v19 = json.loads(v19_path.read_bytes())
v19_payload = REPAIR / 'release_v19_stability_candidate/payload'
v19_changed = {name for name, sha in v19['component_pins'].items()
               if mapping['component_pins'].get(name) != sha}
assert v19_changed == {'tools/board_recording.py', 'tools/board_avatar_gtk.py'}
for relative in v19_changed:
    assert hashlib.sha256((v19_payload / relative).read_bytes()).hexdigest() == v19['component_pins'][relative]
configs = {'config/character_profile.local.json', 'config/persona.xuefei.candidate.json',
           'config/yuki_pair.formal.json', 'config/yuki_accepted_prompt.baseline.txt'}
pins = {name: sha for name, sha in mapping['component_pins'].items()
        if name.endswith('.py') or name in configs}
assert len(pins) == 343
for relative, digest in pins.items():
    assert hashlib.sha256((BASE / relative).read_bytes()).hexdigest() == digest, relative
for directory in (HERE, IDENTITY, M03):
    manifest = json.loads((directory / 'SOURCE_MANIFEST.json').read_bytes())
    for relative, row in manifest['files'].items():
        assert hashlib.sha256((directory / 'after' / relative).read_bytes()).hexdigest() == row['sha256'], relative

sys.path[:0] = [str(BASE), str(IDENTITY),
    r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies']
for name in ('common', 'board', 'board.runtime', 'tools'):
    package = importlib.import_module(name)
    package.__path__ = [str(BASE / name.replace('.', '/'))]
import board.runtime
import tools
import common
common.__path__ = [str(HERE/'after/common'), str(BASE/'common')]
board.runtime.__path__ = [str(HERE/'after/board/runtime'), str(IDENTITY/'after/board/runtime'),
    str(M03/'after/board/runtime'), str(BASE/'board/runtime')]
tools.__path__ = [str(IDENTITY/'after/tools'), str(M03/'after/tools'), str(v19_payload/'tools'), str(BASE/'tools')]
for name in ('tests', 'tests.framework'):
    package = importlib.import_module(name)
    package.__path__ = [str(PROJECT / 'aura' / name.replace('.', '/'))] + list(package.__path__)

import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
