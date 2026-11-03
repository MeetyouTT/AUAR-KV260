import importlib.util
import importlib
import os
from pathlib import Path
import shutil
import sys

import pytest

TASK = Path(__file__).resolve().parent
ORIGINAL = TASK.parent / '2026-11-02_multimodal_dialogue_context/candidate_runtime'
RUNTIME = TASK/'candidate_runtime'
if not RUNTIME.exists():
    shutil.copytree(ORIGINAL, RUNTIME, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'conftest.py'))
for relative, source in (
    ('board/runtime/board_dialogue.py', TASK/'candidate/board/runtime/board_dialogue.py'),
    ('board/runtime/board_memory_policy.py', TASK/'baseline/board/runtime/board_memory_policy.py'),
    ('board/runtime/board_business.py', TASK/'baseline/board/runtime/board_business.py'),
):
    shutil.copyfile(source, RUNTIME/relative)
for relative in ('board/runtime/board_speaker_business.py', 'board/runtime/audio/board_dialogue_jobs.py'):
    source = TASK/'baseline'/relative
    if source.exists():
        shutil.copyfile(source, RUNTIME/relative)
os.environ['AURA_SPEAKER_RUNTIME'] = str(RUNTIME)
(TASK/'tests').mkdir(exist_ok=True)
context_tests = (TASK.parent/'2026-11-02_multimodal_dialogue_context/tests/test_multimodal_context.py').read_text(encoding='utf-8')
# The later named-reply release intentionally speaks the selected face name.
# Spoken assistant replies are saved; raw recognition metadata still is not.
context_tests = context_tests.replace(
    "    assert '画面甲' not in json.dumps(context, ensure_ascii=False)",
    "    assert any(m['role'] == 'assistant' and '画面甲' in m['content'] for m in context['messages'])\n"
    "    assert 'conversation_address' not in context\n"
    "    assert 'voice_state' not in json.dumps(context, ensure_ascii=False)")
(TASK/'tests/test_multimodal_context_current.py').write_text(context_tests, encoding='utf-8')
sys.path.insert(0, str(RUNTIME))
for module in ('board.runtime.board_dialogue', 'board.runtime.board_memory_policy',
               'board.runtime.board_business', 'board.runtime.board_speaker_business',
               'board.runtime.audio.board_dialogue_jobs'):
    importlib.import_module(module)

raise SystemExit(pytest.main([
    '-q', '--confcutdir=' + str(TASK),
    str(TASK/'test_thinking_test.py'),
    str(RUNTIME/'tests/framework/test_board_dialogue.py'),
    str(TASK/'tests/test_multimodal_context_current.py'),
    '--junitxml=' + str(TASK/'TEST_RESULTS.xml'),
]))
