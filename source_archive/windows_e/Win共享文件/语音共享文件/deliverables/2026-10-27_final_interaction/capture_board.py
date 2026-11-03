"""Capture the existing X11 screen and avatar preview, without another sink."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import base64,json,os,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
target=stage/'native_screen.png'
subprocess.run(['python3','-B',str(root/'aura/tools/board_screen_capture.py'),str(target)],env=dict(os.environ,DISPLAY=':0'),check=True,capture_output=True,timeout=8)
with urllib.request.urlopen('http://127.0.0.1:8783/api/frame',timeout=4) as f:avatar=f.read(2_000_001)
assert len(avatar)<=2_000_000
print(json.dumps({'native_screen.png':base64.b64encode(target.read_bytes()).decode(),'native_avatar.jpg':base64.b64encode(avatar).decode()}))
'''.replace('CANDIDATE',repr(c))
data=json.loads(ssh('python3 -B -',script,timeout=20))
for name,raw in data.items():(HERE/name).write_bytes(base64.b64decode(raw))
print(json.dumps({'captured':list(data),'second_native_sink_created':False}))
