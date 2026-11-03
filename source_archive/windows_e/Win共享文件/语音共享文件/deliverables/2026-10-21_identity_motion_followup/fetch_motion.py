"""Read current motion implementation/config; no register IO or movement."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import json
from pathlib import Path
root=Path('/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/runtime/aura')
files=['board/motion/manual_process.py','board/motion/manual.py','board/motion/manual_vsrv.py','config/pan_manual.local.json']
print(json.dumps({p:(root/p).read_text() for p in files if (root/p).is_file()}))
'''
for name,source in json.loads(ssh('python3 -',script)).items():
    target=HERE/('snapshot_'+name.replace('/','_'))
    target.write_text(source,encoding='utf-8')
    print(name)
