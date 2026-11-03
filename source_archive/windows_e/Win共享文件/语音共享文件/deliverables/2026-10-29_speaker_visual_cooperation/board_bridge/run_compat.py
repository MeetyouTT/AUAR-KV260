import bootstrap_bridge
import contextlib,sys
from pathlib import Path
import pytest
H=Path(__file__).resolve().parent;A=bootstrap_bridge.A;BASE=H.parent
names=['test_voice_channel.py','test_spoken_identity_query.py']  # camera fixture needs Linux fcntl; no stub.
with (H/'compat.log').open('w',encoding='utf-8') as output,contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
    result=pytest.main(['-q',*[str(A/'tests/framework'/name) for name in names],str(BASE/'test_native_channel_jobs.py'),
        '--tb=short','--junitxml='+str(H/'compat.xml')])
print((H/'compat.log').read_text(encoding='utf-8'))
sys.exit(result)
