"""Fetch only pinned Python sources; never configuration, business data or logs."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

FILES=('board/runtime/audio/board_asr.py','board/runtime/audio/board_asr_frontend.py',
 'board/runtime/audio/board_dialogue_jobs.py','board/runtime/board_dialogue.py',
 'board/runtime/board_dialogue_client.py','board/runtime/board_business.py',
 'board/runtime/board_speaker_business.py','tools/voice_first_recording.py',
 'tools/board_recording.py','tools/board_business_gui.py','common/board_memory.py')
REMOTE=r'''
import base64,hashlib,json,pathlib
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==EXPECTED
pins=json.loads(raw)['component_sha256'];out={}
for rel in FILES:
 p=root/'runtime/aura'/rel;assert p.is_file() and p.resolve()==p and not p.is_symlink()
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pins[rel]
 out[rel]=dict(sha256=pins[rel],base64=base64.b64encode(raw).decode())
print(json.dumps(out))
'''

if __name__=='__main__':
    baseline=json.loads((HERE/'board_baseline.json').read_text(encoding='utf-8'))
    value=json.loads(ssh('python3 -B -','EXPECTED='+repr(baseline['startup_sha256'])+'\nFILES='+repr(FILES)+'\n'+REMOTE,timeout=25))
    out={}
    for rel,item in value.items():
        assert rel in FILES
        raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
        p=HERE/'source_before'/rel;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():assert p.read_bytes()==raw
        else:p.write_bytes(raw)
        out[rel]=dict(sha256=item['sha256'],bytes=len(raw))
    (HERE/'source_manifest.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out))
