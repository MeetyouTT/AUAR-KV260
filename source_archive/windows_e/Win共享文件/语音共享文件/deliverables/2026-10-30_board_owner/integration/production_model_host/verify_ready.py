"""Metadata-only actual readiness/idempotent entry verification; no inference."""
import hashlib
import datetime
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import manage
from production_runtime import PROJECT,write_json,utc


def main():
    prior,state=manage.latest()
    current=manage.start(wait_seconds=2)
    assert current['status']=='REUSED' and current['session_id']==prior['session_id']
    health=current['health']
    assert health['ok'] is True and health['role']=='model_inference_only'
    assert health['persistence']=='none' and health['request_logging'] is False
    assert health['backend']['model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
    assert health['backend']['tts']=='omnivoice' and health['backend']['num_step']==16
    assert health['backend']['tts_ready'] is True and health['backend']['gpu_coordination']['enforcing'] is True
    from tools.model_inference_host import WindowsTtsProcessProbe
    ownership=WindowsTtsProcessProbe().read(deadline=time.monotonic()+3.,owned_pid=state['same_unique_tts_pid'])
    assert ownership.get('available') and ownership.get('logical_workers')==1
    assert ownership.get('owned_workers')==1 and ownership.get('external_workers')==0
    before=json.loads((HERE/'before.json').read_text(encoding='utf-8-sig'))
    protected=[]
    for row in before['processes']:
        if row['pid'] in {entry['OwningProcess'] for entry in before['listeners'] if entry['LocalPort'] in (11434,8796)}:
            actual=manage.process(row['pid'])
            assert actual is not None and actual['command_sha256']==row['command_sha256']
            assert datetime.datetime.fromisoformat(actual['created_utc'].replace('Z','+00:00')) == datetime.datetime.fromisoformat(row['created_utc'].replace('Z','+00:00'))
            assert actual['executable'].casefold()==row['executable'].casefold()
            protected.append(actual)
    result=dict(status='ACTUAL_PERSISTENT_MODELS_READY_AND_START_REUSED',utc=utc(),
        session_id=current['session_id'],launcher=prior['owner'],main_pid=state['pid'],
        tts_pid=state['same_unique_tts_pid'],fixed_daemon_pid=state['fixed_daemon_pid'],
        lifetime_seconds=None,health=health,tts_ownership=ownership,protected_owners=protected,
        startup=state['startup'],business_database_accessed=False,inference_request_sent=False,
        microphone_or_playback_opened=False,default_legacy_entry_changed=False)
    write_json(HERE/'actual_ready.json',result)
    print(json.dumps(dict(status=result['status'],session_id=result['session_id'],main_pid=result['main_pid'],
        tts_pid=result['tts_pid'],fixed_daemon_pid=result['fixed_daemon_pid'],unique_tts_workers=ownership['logical_workers'])))


if __name__=='__main__':main()
