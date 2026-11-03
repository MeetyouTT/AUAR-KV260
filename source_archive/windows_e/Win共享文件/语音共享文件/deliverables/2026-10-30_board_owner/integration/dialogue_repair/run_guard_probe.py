import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

if __name__=='__main__':
    path=HERE/'memory_guard_probe/probe_prepared_guard.py';raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='86e5de6a47b9a7cab904e0549673d73084472e3ccde1068219c77e0d7e70fd3c'
    value=json.loads(ssh('python3 -B - --aura-root /home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura',raw.decode('utf-8'),timeout=45))
    (HERE/'memory_guard_probe/actual_board.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
