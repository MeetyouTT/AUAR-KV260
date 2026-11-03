"""Read-only public v18 baseline modules, with NO M03-r2 source overlay."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;PROJECT=H.parents[4]
sys.path.insert(0,str(PROJECT/'aura'))
sys.path.insert(0,str(H/'board_integration_v17/local_runtime_v17'))
sys.path.insert(0,r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
for package,paths in (
    ('common',[H/'candidate_h01/after/common']),
    ('board.runtime',[H/'candidate_speaker_close/after/board/runtime',H.parent/'memory_observation_candidate_r2/after/board/runtime',H/'candidate_h01/after/board/runtime']),
    ('tools',[]),
):
    module=importlib.import_module(package)
    module.__path__=[str(path) for path in paths]+list(module.__path__)+[str(PROJECT/'aura'/package.replace('.','/'))]
for package in ('tests','tests.framework'):
    module=importlib.import_module(package)
    module.__path__=[str(PROJECT/'aura'/package.replace('.','/'))]+list(module.__path__)
loaded={}
for name in ('common.board_memory','board.runtime.board_dialogue','board.runtime.board_business',
             'board.runtime.board_memory_policy','tools.production_memory_presentation'):
    module=importlib.import_module(name);path=Path(module.__file__).resolve()
    loaded[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
assert loaded['board.runtime.board_business']['sha256']=='bb82c154ad1d0120b9b188f07a7aa69ec3b3ba6ca15894b1cb0d5ef4a1a1d025'
assert loaded['tools.production_memory_presentation']['sha256']=='8c0cddcdcd91c44eccfd73240826f7b08b8a118c367e15e26295942b9b7ba4aa'
assert loaded['board.runtime.board_memory_policy']['sha256']=='410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5'
import pytest
code=pytest.main(sys.argv[1:])
(H/'candidate_m03_r2/ADDITIONAL_BASELINE_MODULE_PROOF.json').write_bytes((json.dumps(dict(
    pytest_exit_code=code,M03_r2_overlay=False,loaded_modules=loaded),ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
raise SystemExit(code)
