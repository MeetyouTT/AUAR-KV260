import bootstrap
import sys,pytest,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;tmp=H/'test_tmp'/uuid.uuid4().hex
tests=['test_speaker_visual.py','test_turn_attribution_store.py','test_speaker_analysis.py','test_speaker_recorder.py','test_device_attribution_routes.py','test_pcm_lifecycle.py']
raise SystemExit(pytest.main(['-q',*[str(H/name) for name in tests],
 '--junitxml='+str(H/'tests.xml'),'--basetemp='+str(tmp)]+sys.argv[1:]))
