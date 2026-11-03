"""Root-only source install after a normally closed, released model host."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
HOST=HERE.parent.parent/'production_model_host'
CANDIDATE=HERE.parent/'realtime_dialogue_research/first_wait_candidate'
sys.path.insert(0,str(HOST))
import manage

if __name__=='__main__':
    record,state=manage.latest()
    assert record and not manage.same_owner(record)
    assert state['status']=='CLOSED' and state.get('owned_tts_closed') is True
    assert state.get('model_release',{}).get('released') is True
    handoff=json.loads((CANDIDATE/'FREEZE_HANDOFF.json').read_text(encoding='utf-8'))
    targets=('tools/model_inference_host.py','common/model_inference_wire.py','common/inference_output_contract.py')
    backup=HERE/'host_before'
    backup.mkdir(exist_ok=False)
    changes=[]
    for rel in targets:
        item=handoff['artifacts'][rel];raw=(CANDIDATE/item['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        ast.parse(raw,feature_version=(3,10))
        path=PROJECT/'aura'/rel
        expected=handoff['before'].get(rel)
        if expected is None: assert not path.exists()
        else:
            old=path.read_bytes();assert hashlib.sha256(old).hexdigest()==expected
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
        assert not path.is_symlink() and path.parent.resolve()==path.parent
        changes.append((path,raw,dict(path=rel,before_sha256=expected,sha256=item['sha256'])))
    (backup/'closed_owner.json').write_text(json.dumps(dict(record=record,state=state),indent=2)+'\n',encoding='utf-8')
    for path,raw,item in changes:
        tmp=path.with_name(path.name+'.first-wait-new')
        with tmp.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    receipt=dict(status='HOST_SOURCE_INSTALLED_WHILE_NORMAL_CLOSED',previous_session=record['session_id'],
        sources=[item for _,_,item in changes],models_or_configs_changed=False,private_data_accessed=False)
    (HERE/'host_install_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))
