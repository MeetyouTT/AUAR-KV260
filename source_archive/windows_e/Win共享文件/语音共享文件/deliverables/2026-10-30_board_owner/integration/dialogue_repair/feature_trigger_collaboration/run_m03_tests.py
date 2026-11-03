import importlib
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;PROJECT=H.parents[4]
sys.path.insert(0,str(PROJECT/'aura'))
sys.path.insert(0,str(H/'board_integration_v17/local_runtime_v17'))
sys.path.insert(0,r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
for name in ('common','board.runtime'):
    module=importlib.import_module(name)
    module.__path__=[str(H/'candidate_h01_d01_m03/after'/name.replace('.','/'))]+list(module.__path__)+[str(PROJECT/'aura'/name.replace('.','/'))]
module=importlib.import_module('board.runtime')
module.__path__=[str(H/'candidate_speaker_close/after/board/runtime')]+list(module.__path__)
for name in ('tests','tests.framework'):
    module=importlib.import_module(name)
    module.__path__=[str(PROJECT/'aura'/name.replace('.','/'))]+list(module.__path__)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
