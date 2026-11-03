"""Local-only r2 tests with pinned v18 source overlays and original reviews."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

H=Path(__file__).resolve().parent
PROJECT=H.parents[4]
D=H/'candidate_m03_r2'
sys.path.insert(0,str(PROJECT/'aura'))
sys.path.insert(0,str(H/'board_integration_v17/local_runtime_v17'))
sys.path.insert(0,r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
manifest=json.loads((D/'SOURCE_MANIFEST.json').read_bytes())
for relative,row in manifest['files'].items():
    assert hashlib.sha256((D/'after'/relative).read_bytes()).hexdigest()==row['sha256']
review=H/'review_m03_win_inference/test_delete_boundaries.py'
assert hashlib.sha256(review.read_bytes()).hexdigest()=='7528a035ae301b3bf0d3bb0747cb52c322f82b5a1c236102ba5d47915e0c008b'
for package,paths in (
    ('common',[H/'candidate_h01/after/common']),
    ('board.runtime',[D/'after/board/runtime',H/'candidate_speaker_close/after/board/runtime',
                      H.parent/'memory_observation_candidate_r2/after/board/runtime',H/'candidate_h01/after/board/runtime']),
    ('tools',[D/'after/tools']),
):
    module=importlib.import_module(package)
    module.__path__=[str(path) for path in paths]+list(module.__path__)+[str(PROJECT/'aura'/package.replace('.','/'))]
for package in ('tests','tests.framework'):
    module=importlib.import_module(package)
    module.__path__=[str(PROJECT/'aura'/package.replace('.','/'))]+list(module.__path__)
# Original reviewer modules deliberately select their old package paths.
# Preload these exact revised/v18 modules first; no reviewer assertion changes.
loaded={}
for name in ('common.board_memory','board.runtime.board_dialogue','board.runtime.history_delete',
             'board.runtime.board_business','board.runtime.board_speaker_business',
             'board.runtime.board_memory_policy','tools.production_memory_presentation'):
    module=importlib.import_module(name)
    path=Path(module.__file__).resolve()
    loaded[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
assert loaded['board.runtime.history_delete']['sha256']==manifest['files']['board/runtime/history_delete.py']['sha256']
assert loaded['tools.production_memory_presentation']['sha256']==manifest['files']['tools/production_memory_presentation.py']['sha256']
assert loaded['board.runtime.board_memory_policy']['sha256']=='410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5'
import pytest
code=pytest.main(sys.argv[1:])
out=dict(schema='aura.m03-r2.local-module-proof.v1',pytest_exit_code=code,
    independent_test_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),
    independent_assertions_unchanged=True,source_manifest_sha256=hashlib.sha256((D/'SOURCE_MANIFEST.json').read_bytes()).hexdigest(),
    loaded_modules=loaded,production_sources_modified=False,models_or_devices_used=False)
(D/'LAST_MODULE_PROOF.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
raise SystemExit(code)
