import bootstrap
bootstrap.service_module()
import pytest
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
tests=['test_handsfree_dialogue.py','test_voice_barge_in.py','test_board_recording.py','test_voice_channel.py','test_automatic_conversation.py','test_native_grammar.py','test_first_sentence_latency.py']
raise SystemExit(pytest.main(['-q',str(HERE/'test_voice_first.py'),str(HERE/'test_completion.py'),
    *[str(AURA/'tests/framework'/x) for x in tests], '--junitxml='+str(HERE/'voice_first_tests.xml')]))
