"""Single normal owned model lifecycle; no forced termination or daemon changes."""
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, sys, time
from pathlib import Path

TASK=Path(__file__).resolve().parent
PROJECT=TASK.parents[1]/'aura'
HOST=TASK.parent/'2026-10-30_board_owner/integration/production_model_host'
COORD=TASK.parent/'2026-11-02_5090_deployment/CHAT_COORDINATION.json'
OPERATOR='01a1994e-f547-74e1-903d-3591021d67c8'
OLD_SESSION='88fa865670ae4047a30e4b652889b143'
action=sys.argv[1]; assert action in ('stop','apply','start')
phase=(TASK/'DEVICE_MAINTENANCE.json').read_bytes(); owner=json.loads(COORD.read_bytes())['board_maintenance_owner']
assert owner['thread_id']==OPERATOR and owner['permission_active'] is True
assert owner['phase_receipt_sha256']==hashlib.sha256(phase).hexdigest()
assert json.loads(phase)['permission_active'] is True
intent=TASK/('MODEL_'+action.upper()+'_INTENT.json')
with intent.open('x',encoding='utf-8') as f:
    json.dump(dict(action=action,utc=datetime.now(timezone.utc).isoformat(),single_submission=True),f)
sys.path.insert(0,str(HOST))
import manage
original_latest=manage.latest
def latest():
    for attempt in range(6):
        try:return original_latest()
        except PermissionError:
            if attempt==5:raise
            time.sleep(.05)
manage.latest=latest
try:
    if action=='stop':
        stopped=json.loads((TASK/'stop_gui_1_RESULT.json').read_bytes())['board_result']
        assert stopped['status']=='GUI_NORMAL_STOPPED'
        status=manage.status()
        assert status['session_id']==OLD_SESSION and status['status']=='READY' and status['owner_alive']
        (TASK/'MODEL_BEFORE.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
        result=manage.stop(release=True,wait_seconds=30)
        assert result['status']=='CLOSED' and result['state']['model_release']['released'] is True
    elif action=='apply':
        stopped=json.loads((TASK/'MODEL_STOP_RESULT.json').read_bytes())
        assert stopped['status']=='CLOSED' and stopped['state']['model_release']['released']
        record,state=manage.latest()
        assert record['session_id']==OLD_SESSION and not manage.same_owner(record) and state['status']=='CLOSED'
        path=PROJECT/'tools/model_inference_host.py'
        before=(TASK/'host_baseline/model_inference_host.py').read_bytes()
        after=(TASK/'host_candidate/model_inference_host.py').read_bytes()
        assert path.read_bytes()==before
        compile(after,str(path),'exec')
        temp=path.with_name('model_inference_host.five-turn-context.tmp')
        with temp.open('xb') as f:
            f.write(after);f.flush();os.fsync(f.fileno())
        assert path.read_bytes()==before
        os.replace(temp,path)
        assert path.read_bytes()==after
        result=dict(status='HOST_SOURCE_CAS_APPLIED',path=str(path),
            before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest(),context_limit=4096)
    else:
        applied=json.loads((TASK/'MODEL_APPLY_RESULT.json').read_bytes())
        assert applied['status']=='HOST_SOURCE_CAS_APPLIED'
        assert hashlib.sha256((PROJECT/'tools/model_inference_host.py').read_bytes()).hexdigest()==applied['after_sha256']
        record,state=manage.latest()
        assert record['session_id']==OLD_SESSION and not manage.same_owner(record) and state['status']=='CLOSED'
        result=manage.start(wait_seconds=320)
        assert result['status']=='STARTED' and result['health']['backend']['context_limit']==4096
        assert result['health']['backend']['tts_ready'] is True
    (TASK/('MODEL_'+action.upper()+'_RESULT.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','session_id','context_limit','before_sha256','after_sha256') if k in result}))
except BaseException as error:
    (TASK/('MODEL_'+action.upper()+'_ERROR.json')).write_text(json.dumps(dict(error_type=type(error).__name__,message=str(error)[:200])),encoding='utf-8')
    raise
