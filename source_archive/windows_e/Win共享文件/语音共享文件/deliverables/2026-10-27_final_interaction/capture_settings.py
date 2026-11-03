"""Temporarily show settings for screenshot QA, then restore the exact page/layer."""
import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
script = r'''
import base64,json,os,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
def state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def post(value):
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=5) as f:r=json.load(f)
    assert r['ok'],r
before=state();assert before['phase']=='IDLE' and before['audio_output_state']=='IDLE_READY'
assert before['manual_pan']['automatic_following'] is False and before['handsfree_dialogue']['enabled'] is False
try:
    post({'type':'ui_layer','layer':'debug'});post({'type':'ui_page','page':'settings'});time.sleep(.7)
    target=stage/'native_settings.png'
    subprocess.run(['python3','-B',str(root/'aura/tools/board_screen_capture.py'),str(target)],env=dict(os.environ,DISPLAY=':0'),check=True,capture_output=True,timeout=8)
    encoded=base64.b64encode(target.read_bytes()).decode()
finally:
    post({'type':'ui_page','page':before['ui_page']});post({'type':'ui_layer','layer':before['ui_layer']})
after=state();assert after['ui_page']==before['ui_page'] and after['ui_layer']==before['ui_layer']
assert after['manual_pan']['pulse_us']==before['manual_pan']['pulse_us']
print(json.dumps({'image':encoded,'restored_page':after['ui_page'],'restored_layer':after['ui_layer']}))
'''.replace('CANDIDATE', repr(c))
v = json.loads(ssh('python3 -B -', script, timeout=25))
(HERE / 'native_settings.png').write_bytes(base64.b64decode(v.pop('image')))
print(json.dumps(v))
