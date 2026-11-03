"""Read source changes before re-applying the small UI/profile patch."""
import difflib, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
names=['tools/board_avatar_gtk.py','board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py','tools/motion_queue.py']
script=r'''
import hashlib,json,subprocess
from pathlib import Path
root=Path(ROOT)/'aura';names=NAMES
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'files':{n:(root/n).read_text() for n in names},
 'raw_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
 'text_sha256':{n:hashlib.sha256((root/n).read_text().encode()).hexdigest() for n in names}}))
'''.replace('ROOT',repr(c['source_runtime'])).replace('NAMES',repr(names))
value=json.loads(ssh('python3 -B -',script,timeout=15))
diffs=[]
for name,text in value.pop('files').items():
    target=HERE/'current_base'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8',newline='\n')
    old=HERE/'board_before'/name
    if not old.exists():old=HERE.parent/'2026-10-26_profile_memory/board_base'/name
    diffs.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),text.splitlines(True),fromfile='before/'+name,tofile='current/'+name))
(HERE/'source_rebaseline.diff').write_text(''.join(diffs),encoding='utf-8')
(HERE/'current_base.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value));print(''.join(diffs))
