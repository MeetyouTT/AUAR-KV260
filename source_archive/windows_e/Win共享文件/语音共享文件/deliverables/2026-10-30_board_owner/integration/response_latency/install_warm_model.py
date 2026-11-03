"""Install one reviewed host source only after confirmed normal owned-model release."""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'production_model_host'))
import manage
from production_runtime import utc,write_json

def sha(raw):return hashlib.sha256(raw).hexdigest()

if __name__=='__main__':
    spec=json.loads((HERE/'warm_model_candidate/manifest.json').read_text(encoding='utf-8'))
    record,state=manage.latest()
    assert record and state['status']=='CLOSED' and manage.same_owner(record) is False
    assert state['owned_tts_closed'] is True and state['model_release']['released'] is True
    target=PROJECT/spec['target'];candidate=HERE/'warm_model_candidate/after'/spec['target']
    before=target.read_bytes();after=candidate.read_bytes()
    assert sha(before)==spec['before_sha256'] and sha(after)==spec['after_sha256']
    backup=HERE/'windows_source_before';backup.mkdir(exist_ok=False)
    (backup/'model_inference_host.py').write_bytes(before)
    temporary=target.with_name(target.name+'.warm-model-new')
    with temporary.open('xb') as stream:stream.write(after);stream.flush();os.fsync(stream.fileno())
    assert target.read_bytes()==before
    os.replace(temporary,target)
    assert sha(target.read_bytes())==spec['after_sha256']
    result=dict(status='OWNED_HOST_SOURCE_UPDATED_AFTER_NORMAL_RELEASE',recorded_utc=utc(),
        target=spec['target'],before_sha256=spec['before_sha256'],after_sha256=spec['after_sha256'],
        previous_session=record['session_id'],owned_tts_closed=True,owned_model_released=True,
        keep_alive=-1,other_model_or_daemon_changed=False,weights_moved=False)
    write_json(HERE/'windows_source_installed.json',result)
    write_json(HERE.parent/'production_model_host/SOURCE_REVISION.json',result)
    print(json.dumps(result))
