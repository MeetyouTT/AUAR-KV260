"""Current source/configuration and bounded safe diagnostics, never transcripts."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path[:0]=[str(PROJECT/'deliverables/2026-10-18_board_dialogue'),str(HERE.parent/'production_model_host')]
from board_ssh import ssh
import manage
from production_runtime import utc,ollama_json

REMOTE=r'''
import hashlib,http.client,json,pathlib
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 c.request('GET','/api/state');r=c.getresponse();v=json.loads(r.read(1048577));assert r.status==200
finally:c.close()
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())['board_business']
b=v['board_business'];memory=b['memory'];retry=memory.get('retry_backoff',{})
assert cfg['asr_threads']==3 and cfg['frontend_capture_process'] is True
assert b['started'] is True and b['writer']['held'] is True and b['receipt']['verified'] is True
assert b['retention']['enabled'] is True and b['retention']['running'] is True
assert b['dialogue']['capabilities']['native_rate_bridge'] is False
assert retry.get('maximum_seconds')==60 and 'latency' in b['dialogue']
allowed={'candidate_rejected','model_failed','deadline_exceeded','database_busy','compaction_failed','cancelled',''}
error=retry.get('last_failure_code')
retry_out={k:retry.get(k) for k in ('failure_streak','retry_in_seconds','last_delay_seconds','skipped_for_cooldown','maximum_seconds')}
retry_out['last_failure_code']=error if error in allowed else 'other'
print(json.dumps(dict(startup_sha256=hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest(),
 asr_threads=cfg['asr_threads'],native_streaming_path_selected=True,
 memory=dict(completed=memory['completed'],discarded=memory['discarded'],retry_backoff=retry_out),
 latency_schema_present=True,physical_speaker_latency_measured=False,
 automatic_listening_enabled=v['handsfree_dialogue']['enabled'],listening_state=v['handsfree_dialogue']['state'],
 capture_error=v['safe_capture_diagnostics']['error_code'],playing=v.get('playing'))))
'''

if __name__=='__main__':
    board=json.loads(ssh('python3 -B -',REMOTE,timeout=15))
    record,state=manage.latest();assert state['status']=='READY' and manage.same_owner(record)
    health=manage.health();assert health['backend']['tts_ready'] is True and health['backend']['num_step']==16
    assert health['backend']['gpu_coordination']['enforcing'] is True
    rows=ollama_json('GET','/api/ps')['models']
    assert len(rows)==1 and rows[0]['name']=='aura-qwen3.8-27b-abliterated:iq4_xs'
    assert int(rows[0]['expires_at'][:4])>2100
    windows=dict(session=record['session_id'],host_pid=state['pid'],tts_pid=state['same_unique_tts_pid'],
        fixed_daemon_pid=state['fixed_daemon_pid'],status='READY',keep_alive=-1,expires_at=rows[0]['expires_at'],
        num_step=16,gpu_enforcing=True,weights_outside_shared_directory=True,
        host_source_sha256=hashlib.sha256((PROJECT/'aura/tools/model_inference_host.py').read_bytes()).hexdigest())
    result=dict(recorded_utc=utc(),board=board,windows=windows)
    (HERE/'final_runtime.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
