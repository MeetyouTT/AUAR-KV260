"""Read live service state, source hashes and actual screen without starting capture."""
import base64
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

candidate = json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote = r'''
import base64,hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
c=CANDIDATE
root=Path(c['runtime']);stage=Path(c['stage'])
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4) as r:return json.load(r)
sys.path.insert(0,str(root/'aura'))
from tools.board_screen_capture import capture
screen=stage/'live_screen.png';size=capture(screen)
report={'state':get(8783,'/api/state'),'camera':get(8790,'/health'),
        'pc_health':get(8792,'/health','192.168.50.1'),
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'ui_service':subprocess.check_output(['systemctl','is-active','aura-avatar-ui.service'],text=True).strip(),
        'unit':subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True),
        'source_hashes':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in c['files']},
        'launch':json.loads((root/'launch.json').read_text()),'screen_size':size}
print(json.dumps({'report':report,'image':base64.b64encode(screen.read_bytes()).decode()}))
'''.replace('CANDIDATE',repr(candidate))
result=json.loads(ssh('python3 -',remote,timeout=35))
(HERE/'live_screen.png').write_bytes(base64.b64decode(result['image'],validate=True))
(HERE/'current_state.json').write_text(json.dumps(result['report'],ensure_ascii=False,indent=2),encoding='utf-8')
assert result['report']['source_hashes']==candidate['files']
state=result['report']['state']
print(json.dumps({'service':result['report']['ui_service'],'phase':state['phase'],
    'automatic':state['automatic_conversation'],'recording':state['local_recording']['state'],
    'transcription':state['local_transcription']['state'],'source_hashes_match':True,
    'screen_size':result['report']['screen_size']},ensure_ascii=True))
