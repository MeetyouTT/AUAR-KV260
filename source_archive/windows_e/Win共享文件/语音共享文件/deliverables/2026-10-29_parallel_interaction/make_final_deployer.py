"""Reuse the previously verified guarded transaction, with distinct new evidence."""
from pathlib import Path
H=Path(__file__).resolve().parent
s=(H.parent/'2026-10-29_audio_animation_polish/deploy_board.py').read_text(encoding='utf-8')
old='from board_guard import H,SCRIPT,capture,same,ssh'
assert s.count(old)==1
s=s.replace(old,"from pathlib import Path\nimport sys,xml.etree.ElementTree as ET\nH=Path(__file__).resolve().parent\nsys.path.insert(0,str(H.parent/'2026-10-29_audio_animation_polish'))\nfrom board_guard import SCRIPT,capture,same,ssh")
s=s.replace("H/'preflight.json'","H/'board_preflight.json'").replace("H/'candidate.json'","H/'board_candidate.json'")
old="assert json.loads((H/'native_visual.json').read_text())['status']=='PASS'\nassert json.loads((H/'renderer_after.json').read_text())['status']=='PASS'"
new="suite=ET.parse(H/'final_tests.xml').getroot()\nassert all(int(node.get('failures',0))==0 and int(node.get('errors',0))==0 for node in suite.iter('testsuite'))\nassert json.loads((H/'final_installation.json').read_text())['status']=='INSTALLED_FINAL'\nassert json.loads((H/'final_ready_fixed.json').read_text())['status']=='READY'"
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('-aura-audio-animation-20261029.conf','-aura-identity-bridge-20261030.conf')
s=s.replace("H/'deployment.json'","H/'board_deployment.json'")
s=s.replace("H/'deployment_transport_failure.json'","H/'board_deployment_transport_failure.json'")
compile(s,'deploy_final_board.py','exec');(H/'deploy_final_board.py').write_text(s,encoding='utf-8')
print('Guarded board switch helper prepared; no deployment performed')
