"""Run existing host/channel/memory regressions against candidate modules."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;APP=HERE.parents[1]/'aura'
sys.path.insert(0,str(APP))
import common,tools
common.__path__=[str(HERE/'action_sources/common'),*common.__path__]
tools.__path__=[str(HERE/'action_sources/tools'),*tools.__path__]
import board.runtime.audio
board.runtime.audio.__path__=[str(HERE/'action_sources/board/runtime/audio'),*board.runtime.audio.__path__]
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider',
    str(APP/'tests/test_speech_motion.py'),
    *[str(APP/'tests/framework'/name) for name in (
        'test_voice_channel.py','test_first_sentence_latency.py','test_channel_jobs.py',
        'test_memory_controls.py','test_session_memory.py','test_conversation_store.py',
        'test_identity_voice.py') if (APP/'tests/framework'/name).is_file()]]))
