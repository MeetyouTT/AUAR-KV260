"""Deploy a standalone visible sampler; do not replace the active avatar UI."""
import base64
import json
from pathlib import Path
import sys
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
sid=uuid.uuid4().hex
payload=base64.b64encode((ROOT/'aura/tools/board_speaker_sampler.py').read_bytes()).decode('ascii')
script='''import base64,json,os,pathlib,subprocess
directory=pathlib.Path('/home/root/aura-speaker-test-visible-20261020')
directory.mkdir(exist_ok=True,mode=0o700)
target=directory/'sampler.py'
target.write_bytes(base64.b64decode(PAYLOAD))
environment=dict(os.environ,DISPLAY=':0',PYTHONUNBUFFERED='1')
for item in pathlib.Path('/proc').iterdir():
    if not item.name.isdigit():continue
    try:
        if b'/tools/board_avatar_gtk.py' not in (item/'cmdline').read_bytes():continue
        for entry in (item/'environ').read_bytes().split(b'\\0'):
            key,sep,value=entry.partition(b'=')
            if key in (b'DISPLAY',b'XAUTHORITY'):environment[key.decode()]=value.decode()
        break
    except (OSError,ValueError):pass
with (directory/'stdout.log').open('a') as output,(directory/'stderr.log').open('a') as error:
    process=subprocess.Popen(['python3','-B',str(target),'--session',SESSION,'--restore-monitor'],
        env=environment,stdin=subprocess.DEVNULL,stdout=output,stderr=error,start_new_session=True)
print(json.dumps({'pid':process.pid,'session_id':SESSION,'script':str(target),'scope':'VISIBLE_CLICK_ONLY_NO_AUTOMATIC_CAPTURE'}))
'''.replace('PAYLOAD',repr(payload)).replace('SESSION',repr(sid))
value=json.loads(ssh('python3 -',script,timeout=15))
(HERE/'visible_sampler_deployment.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
