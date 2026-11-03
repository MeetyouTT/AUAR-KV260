"""Inspect the actual board sampler state and optionally its real X11 screen."""
import argparse
import base64
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
parser=argparse.ArgumentParser();parser.add_argument('--screenshot',action='store_true');args=parser.parse_args()
sid=json.loads((HERE/'visible_sampler_deployment.json').read_text(encoding='utf-8'))['session_id']
capture_code=base64.b64encode((ROOT/'aura/tools/board_screen_capture.py').read_bytes()).decode('ascii')
script='''import base64,json,pathlib,os
directory=pathlib.Path.home()/'.local/share/aura/speaker_test_recordings'/SESSION
path=directory/'sampler_state.json'
if not path.is_file():
    print(json.dumps({'error':pathlib.Path('/home/root/aura-speaker-test-visible-20261020/stderr.log').read_text()[-3000:]}))
else:
    result={'state':json.loads(path.read_text())}
    if SCREENSHOT:
        scope={'__name__':'speaker_screen_capture'}
        exec(compile(base64.b64decode(CAPTURE_CODE),'capture.py','exec'),scope)
        image=directory/'screen.png';scope['capture'](image)
        result['screen_base64']=base64.b64encode(image.read_bytes()).decode('ascii')
    print(json.dumps(result))
'''.replace('SESSION',repr(sid)).replace('SCREENSHOT',repr(args.screenshot)).replace('CAPTURE_CODE',repr(capture_code))
value=json.loads(ssh('python3 -',script,timeout=20))
if 'screen_base64' in value:
    (HERE/'visible_sampler_screen.png').write_bytes(base64.b64decode(value.pop('screen_base64')))
(HERE/'visible_sampler_state.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=False))
if 'error' in value:raise SystemExit(1)
