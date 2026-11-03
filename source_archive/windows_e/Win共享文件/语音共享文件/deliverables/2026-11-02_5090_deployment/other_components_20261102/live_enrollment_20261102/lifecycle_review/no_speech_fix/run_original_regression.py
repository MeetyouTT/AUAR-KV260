"""Load the selected exact modules, then run existing public synthetic tests."""
import importlib.util,os
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('no_speech_review_harness',HERE/'test_no_speech_pipeline.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
mode=os.environ.get('AURA_NO_SPEECH_REVIEW_MODE','candidate')
tests=module.RUNTIME/'tests/framework'
raise SystemExit(pytest.main([str(tests/name) for name in ('test_board_dialogue_jobs.py','test_board_dialogue.py','test_board_recording.py')]+
    ['-q','--disable-warnings','--tb=short','--junitxml='+str(HERE/(mode.upper()+'_ORIGINAL_REGRESSION.xml'))]))
