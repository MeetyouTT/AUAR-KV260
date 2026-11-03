"""Execute remotely only for an explicitly requested speaker test clip."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import urllib.request
import wave

SESSION = 'SESSION_TOKEN_PLACEHOLDER'
CLIP = CLIP_NUMBER_PLACEHOLDER
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def playback_active():
    with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:
        state = json.load(response)
    if type(state.get('playing')) is not bool or type(state.get('paused')) is not bool:
        raise ValueError('Invalid playback owner state')
    automatic = state.get('automatic_conversation',{})
    return (state['playing'] or state['paused'] or state.get('phase') != 'IDLE'
            or automatic.get('enabled') is not False
            or state.get('handsfree_dialogue',{}).get('enabled') is True)


lines = subprocess.check_output(['ps','-eo','args'],universal_newlines=True).splitlines()
roots = set()
for line in lines:
    try: args = shlex.split(line)
    except ValueError: continue
    for arg in args:
        if arg.endswith('/tools/board_avatar_gtk.py'):
            root = Path(arg).resolve().parents[1]
            if (root/'board/runtime/audio/capture.py').is_file(): roots.add(str(root))
if len(roots) != 1: raise RuntimeError('Need one active verified UI runtime')
sys.path.insert(0,roots.pop())
from board.runtime.audio.capture import Mcp01Capture

directory = Path.home()/'.local/share/aura/speaker_test_recordings'/SESSION
directory.mkdir(parents=True,exist_ok=True,mode=0o700)
os.chmod(directory,0o700)
path = directory/('clip-%02d.wav' % CLIP)
if path.exists(): raise ValueError('Never overwrite a recording')
with Mcp01Capture(playback_active,max_seconds=20) as capture:
    capture.start()
    print(json.dumps({'event':'CAPTURE_STARTED','seconds':20,'exclusive_capture_owned':True}),flush=True)
    deadline = time.monotonic()+21
    while capture.snapshot()['state']=='RECORDING' and time.monotonic()<deadline:
        if playback_active():
            capture.cancel()
            raise RuntimeError('Playback/automatic conversation became active; capture cancelled')
        time.sleep(.1)
    capture.stop()
    clip = capture.take()
buffer = io.BytesIO()
with wave.open(buffer,'wb') as output:
    output.setparams((1,2,16000,0,'NONE','not compressed'))
    output.writeframes(clip.pcm)
raw = buffer.getvalue()
fd = os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as output: output.write(raw)
meta = dict(clip.metadata(),session_id=SESSION,clip_number=CLIP,
            source='ACTUAL_MCP01_EXPLICIT_SPEAKER_TEST',wav_sha256=hashlib.sha256(raw).hexdigest(),
            remote_wav=str(path),consent_scope='explicit_ready_start_sampling')
with path.with_suffix('.json').open('x',encoding='utf-8') as output: json.dump(meta,output,indent=2)
os.chmod(str(path.with_suffix('.json')),0o600)
print(json.dumps({'metadata':meta,'wav_base64':base64.b64encode(raw).decode('ascii')}))
