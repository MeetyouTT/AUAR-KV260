"""Fetch pinned source code only for the intermittent capture failure review."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import base64,hashlib,json,pathlib
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==SPEC['startup_sha256']
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
names={'board_frontend_process.py','board_frontend_auto.py','board_capture.py','automatic_capture.py',
 'board_pcm_queue.py','capture.py','board_asr_frontend.py','board_audio_frontend.py'}
sources={}
for rel,pin in json.loads(raw)['component_sha256'].items():
 if not rel.startswith('board/runtime/audio/') or pathlib.Path(rel).name not in names:continue
 path=root/'runtime/aura'/rel;assert path.is_file() and not path.is_symlink() and path.resolve()==path
 source=path.read_bytes();assert hashlib.sha256(source).hexdigest()==pin
 sources[rel]=dict(sha256=pin,base64=base64.b64encode(source).decode())
print(json.dumps(dict(startup_sha256=SPEC['startup_sha256'],sources=sources)))
'''

if __name__=='__main__':
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    result=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\n'+REMOTE,timeout=20))
    directory=HERE/'capture_sources';directory.mkdir(exist_ok=True)
    for rel,item in result['sources'].items():
        raw=base64.b64decode(item.pop('base64'));assert hashlib.sha256(raw).hexdigest()==item['sha256']
        path=directory/rel;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
    (directory/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
