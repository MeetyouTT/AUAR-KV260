import bootstrap_bridge
import contextlib,sys
from pathlib import Path
import pytest
H=Path(__file__).resolve().parent
with (H/'tests.log').open('w',encoding='utf-8') as output,contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
    result=pytest.main([str(H/'test_face_bridge.py'),'-q','--tb=short','--junitxml='+str(H/'tests.xml')])
print((H/'tests.log').read_text(encoding='utf-8'))
sys.exit(result)
