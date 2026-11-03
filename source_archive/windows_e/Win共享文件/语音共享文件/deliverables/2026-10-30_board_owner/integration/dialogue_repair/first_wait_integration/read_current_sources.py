"""Read pinned public runtime sources only; no private records or device changes."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import base64,hashlib,json,pathlib
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='ae47311619310420b3215770b676c48a9f1d8e3d33d02c72fa04e21186ec903b'
startup=json.loads(raw);pins=startup['component_sha256']
names=['board/runtime/board_business.py','board/runtime/board_dialogue.py',
       'board/runtime/board_dialogue_client.py','common/model_inference_wire.py']
names += [k for k in pins if k.startswith('tools/') and 'production' in k and k.endswith('.py')]
files={}
for rel in names:
 p=root/'runtime/aura'/rel
 assert not p.is_symlink() and p.stat().st_size<1024*1024
 data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==pins[rel]
 files[rel]={'sha256':pins[rel],'base64':base64.b64encode(data).decode()}
print(json.dumps({'startup_sha256':hashlib.sha256(raw).hexdigest(),
 'source_manifest_sha256':hashlib.sha256((root/'production_source_manifest.json').read_bytes()).hexdigest(),
 'component_sha256':pins,'files':files}))
'''

if __name__ == '__main__':
    result=json.loads(ssh('python3 -B -',REMOTE,timeout=25))
    for rel, item in result.pop('files').items():
        raw=base64.b64decode(item['base64'],validate=True)
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        path=HERE/'before'/rel
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
    (HERE/'baseline_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PINNED_PUBLIC_SOURCES_READ','startup_sha256':result['startup_sha256']}))
