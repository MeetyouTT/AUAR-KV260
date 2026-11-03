"""Same 16 public memory contracts with the two H01 source modules selected."""
import importlib.util
from pathlib import Path
import sys
import unittest
from v18_common import REPAIR, CORE, pinned

BASE = REPAIR / 'animation_thinking_collaboration/runtime_v16'
sys.path.insert(0, str(BASE))

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

if __name__ == '__main__':
    for relative, name in [('common/board_memory.py','common.board_memory'),
                           ('board/runtime/board_dialogue.py','board.runtime.board_dialogue')]:
        source, before, after=CORE[relative]
        path=REPAIR/source;pinned(path,after);load(name,path)
    module=load('merged_public_observation_contracts', REPAIR/'memory_observation_candidate_r2/tests/test_observation_origin.py')
    suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
