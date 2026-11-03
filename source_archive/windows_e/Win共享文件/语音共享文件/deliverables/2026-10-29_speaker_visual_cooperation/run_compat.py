import bootstrap
import sys,pytest,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;A=bootstrap.A;tmp=H/'test_tmp'/uuid.uuid4().hex
names=['test_speaker_identity.py','test_profile_memory.py','test_long_conversation.py','test_memory_controls.py',
       'test_voice_channel.py','test_spoken_identity_query.py']
raise SystemExit(pytest.main(['-q',*[str(A/'tests/framework'/name) for name in names],str(H/'test_native_channel_jobs.py'),
 '--junitxml='+str(H/'compat_tests.xml'),'--basetemp='+str(tmp)]+sys.argv[1:]))
