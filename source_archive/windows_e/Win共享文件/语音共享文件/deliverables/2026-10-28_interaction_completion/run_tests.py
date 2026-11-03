import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path[:0]=[str(AURA),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
import tools,board,common
tools.__path__=[str(HERE/'candidate_source/tools'),str(AURA/'tools')]
import pytest
tests=['test_board_recording.py','test_streaming_dialogue.py','test_handsfree_dialogue.py','test_barge_in.py','test_native_grammar.py','test_first_sentence_latency.py']
tests=[str(AURA/'tests/framework'/x) for x in tests if (AURA/'tests/framework'/x).exists()]
raise SystemExit(pytest.main(['-q',str(HERE/'test_completion.py'),*tests,'--junitxml='+str(HERE/'tests.xml')]))

