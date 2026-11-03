"""Reuse the reviewed idle-only host deployment for the memory routing patch."""
from pathlib import Path
import xml.etree.ElementTree as ET
H=Path(__file__).resolve().parent
suite=ET.parse(H/'voice_first_tests.xml').getroot()
assert all(int(s.get('failures','0'))==0 and int(s.get('errors','0'))==0 for s in suite.iter('testsuite'))
text=(H/'restart_host.py').read_text(encoding='utf-8')
text=text.replace('voice-device-skills-20261028-r5','voice-device-skills-20261028-r6').replace('voice-device-skills-20261028-r4','voice-device-skills-20261028-r5')
text=text.replace("names=['tools/board_model_host.py','common/voice_service_capabilities.py']", "names=['tools/device_client.py','tools/voice_channel_source.py','common/voice_service_capabilities.py']")
text=text.replace('before_host_r5','before_host_r6').replace('host_hotfix.json','host_memory_hotfix.json').replace('host_restart_launch.log','host_memory_restart_launch.log')
assert "names=['tools/device_client.py'" in text
compile(text,'memory-restart','exec')
(H/'restart_memory_host.py').write_text(text,encoding='utf-8')
print('Prepared guarded host-only memory update')
