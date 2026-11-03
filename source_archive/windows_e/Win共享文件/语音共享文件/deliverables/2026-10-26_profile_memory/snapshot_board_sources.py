import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import hashlib,json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='16a07283-9e14-45e6-816d-3bda4cf333a7','Board boot changed; inspect actual runtime first'
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
command=Path('/proc/%d/cmdline'%pid).read_bytes().replace(b'\0',b' ').decode()
assert '/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/startup/launcher.py' in command
root=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/runtime/aura')
names=['board/runtime/audio/voice_channel.py','board/runtime/audio/channel_jobs.py','tools/board_avatar_gtk.py']
files={name:(root/name).read_text() for name in names}
print(json.dumps(dict(root=str(root),boot=boot,ui_pid=pid,files=files,
                     sha256={name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()})))
'''
value=json.loads(ssh('python3 -B -',script,timeout=15))
for name,text in value.pop('files').items():
    path=HERE/'board_base'/name;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError('Preserve original board snapshot')
    path.write_text(text,encoding='utf-8')
(HERE/'board_base.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
