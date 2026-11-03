"""Source-isolated v13/v14 comparison with synthetic stores and fake clients."""
import importlib.util
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
PROJECT = HERE.parents[5]
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(PROJECT/'aura'))
sys.path.insert(0, r'E:\Win共享文件\tmp\aura-validation-venv\Lib\site-packages')
import pytest


def load(name, relative, folder):
    spec = importlib.util.spec_from_file_location(name, HERE/folder/relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'targeted'
    assert mode in ('baseline', 'targeted', 'regression')
    folder = 'before' if mode == 'baseline' else 'after'
    import common
    common.board_memory = load('common.board_memory', 'common/board_memory.py', folder)
    load('common.board_memory_backoff', 'common/board_memory_backoff.py', 'before')
    load('board.runtime.board_memory_policy', 'board/runtime/board_memory_policy.py', folder)
    paths = [str(HERE/'tests')]
    if mode == 'regression':
        paths += [str(PARENT/'tests')]
        paths += [str(PROJECT/'aura/tests/framework'/name) for name in (
            'test_board_memory.py', 'test_board_memory_policy.py', 'test_board_memory_completion.py',
            'test_board_memory_review.py', 'test_board_memory_search_clear.py', 'test_board_timeline_clock.py')]
        paths += [str(PARENT.parent/'guard_session_candidate/tests/test_session.py')]
    output = HERE/('test_'+mode)
    output.mkdir(exist_ok=True)
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output/'tmp'),
        '--junitxml', str(output/'results.xml')] + paths
    if mode == 'baseline':
        args += ['-k', 'test_valid_structured_camera_compaction_needs_no_model or test_known_camera_wording_can_fail_old_free_form_summary']
    if mode == 'regression':
        args += ['-k', 'not test_character_address_understanding_keeps_raw_asr_in_memory and not test_addressed_explicit_commands_still_write_on_board_with_raw_sources']
    raise SystemExit(pytest.main(args))
