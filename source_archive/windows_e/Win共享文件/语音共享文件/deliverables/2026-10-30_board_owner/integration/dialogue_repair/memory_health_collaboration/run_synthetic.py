"""Offline pytest runner using existing installed pytest; no new environment."""
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(PROJECT / 'aura'))
sys.path.insert(0, r'E:\Win共享文件\tmp\aura-validation-venv\Lib\site-packages')
import pytest


def load(name, relative, candidate=False):
    target = HERE / ('after' if candidate and (HERE/'after'/relative).is_file() else 'before') / relative
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'baseline'
    if mode not in ('baseline', 'candidate', 'regression', 'baseline_regression', 'baseline_restart'):
        raise ValueError('Unknown synthetic mode')
    candidate = mode not in ('baseline', 'baseline_regression', 'baseline_restart')
    import common
    common.board_memory = load('common.board_memory', 'common/board_memory.py')
    load('common.board_memory_backoff', 'common/board_memory_backoff.py', candidate)
    load('board.runtime.board_memory_policy', 'board/runtime/board_memory_policy.py', candidate)
    paths = [str(HERE / 'tests')]
    if mode in ('regression', 'baseline_regression'):
        paths += [str(PROJECT/'aura/tests/framework'/name) for name in (
            'test_board_memory.py', 'test_board_memory_policy.py', 'test_board_memory_completion.py',
            'test_board_memory_review.py', 'test_board_memory_search_clear.py', 'test_board_timeline_clock.py')]
    if mode == 'baseline_regression':
        paths = [str(PROJECT/'aura/tests/framework/test_board_memory_policy.py')]
    if mode == 'baseline_restart':
        paths = [str(HERE/'tests/test_restart_generation.py')]
    result_dir = HERE / ('test_' + mode)
    result_dir.mkdir(exist_ok=True)
    arguments = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(result_dir/'tmp'),
        '--junitxml', str(result_dir/'results.xml')] + paths
    if mode == 'baseline_regression':
        arguments += ['-k', 'test_character_address_understanding_keeps_raw_asr_in_memory or test_addressed_explicit_commands_still_write_on_board_with_raw_sources']
    if mode == 'regression':
        # These three exact old fixtures expect the retired character's aliases.
        # Their unchanged baseline failure is retained in baseline_regression.
        # Equivalent current-character tests live in the isolated tests folder.
        arguments += ['-k', 'not test_character_address_understanding_keeps_raw_asr_in_memory and not test_addressed_explicit_commands_still_write_on_board_with_raw_sources']
        paths_guard = HERE.parent/'guard_session_candidate/tests/test_session.py'
        arguments += [str(paths_guard)]
    raise SystemExit(pytest.main(arguments))
