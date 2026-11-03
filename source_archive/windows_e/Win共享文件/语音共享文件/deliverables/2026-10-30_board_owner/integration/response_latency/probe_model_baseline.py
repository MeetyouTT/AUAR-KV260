"""One existing public pure-model case with bounded phase timing, no dialogue data."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
HOST=HERE.parent/'production_model_host'
PROJECT=HERE.parents[3]
sys.path[:0]=[str(HOST),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
import manage
from production_runtime import utc

path=HOST/'public_board_name_chain.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='a1aa2725b269f69e572e52c8fd0c41097c39fb9c5a9a9bcedb15d384db65f966'
spec=importlib.util.spec_from_file_location('_public_latency_base',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
remote=module.REMOTE
changes={
    "before=health()": """if CLOSED_UI:
 import subprocess
 u=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
 assert u==dict(MainPID='0',ActiveState='inactive')
else:
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
 try:
  c.request('GET','/api/state');r=c.getresponse();v=json.loads(r.read(1048577));assert r.status==200
  assert v.get('playing') is False and v.get('board_business',{}).get('dialogue',{}).get('pending') is False
  assert v.get('handsfree_dialogue',{}).get('conversation_entered') is False
  assert v.get('safe_capture_diagnostics',{}).get('capture',{}).get('speech_active') is False
 finally:c.close()
before=health()""",
    "response=client.request('llm',llm,deadline=deadline)": """chain_start=time.monotonic()
response=client.request('llm',llm,deadline=deadline)
llm_wall_ms=(time.monotonic()-chain_start)*1000
llm_metrics={k:v for k,v in response.get('result',{}).get('metrics',{}).items()
 if k in ('total_duration_ms','load_duration_ms','prompt_eval_count','prompt_eval_duration_ms','eval_count','eval_duration_ms') and type(v) in (int,float)}""",
    "response=client.request('tts',tts,deadline=deadline)": """tts_start=time.monotonic()
response=client.request('tts',tts,deadline=deadline)
tts_wall_ms=(time.monotonic()-tts_start)*1000
chain_wall_ms=(time.monotonic()-chain_start)*1000""",
    "public_reply=text.strip(),": "timings=dict(llm_wall_ms=llm_wall_ms,tts_wall_ms=tts_wall_ms,model_chain_wall_ms=chain_wall_ms,llm_metrics=llm_metrics),",
}
for old,new in changes.items():
    assert remote.count(old)==1
    remote=remote.replace(old,new)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',choices=('baseline','warm','after'),required=True)
    parser.add_argument('--closed-ui',action='store_true')
    args=parser.parse_args()
    output=HERE/('model_'+args.label+'.json')
    assert not output.exists(), 'Preserve the existing measurement'
    record,state=manage.latest()
    assert record and state['status']=='READY' and manage.same_owner(record)
    bound=dict(host_session_id=record['session_id'],main_pid=state['pid'],tts_pid=state['same_unique_tts_pid'],fixed_daemon_pid=state['fixed_daemon_pid'])
    result=json.loads(ssh('python3 -B -','CLOSED_UI='+repr(args.closed_ui)+'\n'+remote,timeout=90))
    after,after_state=manage.latest()
    assert after==record and manage.same_owner(record)
    assert after_state['pid']==bound['main_pid'] and after_state['same_unique_tts_pid']==bound['tts_pid']
    result.update(recorded_utc=utc(),model_owner_binding=bound,actual_user_turn=False)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],timings=result['timings'],actual_user_turn=False,asr_called=False,audio_played=False)))
