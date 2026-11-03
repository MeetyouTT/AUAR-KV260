"""Root-only public board Ethernet compact LLM/RAM TTS check with UI closed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
HOST=HERE.parent.parent/'production_model_host'
sys.path[:0]=[str(HOST),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
import manage

source=HOST/'public_board_name_chain.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='a1aa2725b269f69e572e52c8fd0c41097c39fb9c5a9a9bcedb15d384db65f966'
spec=importlib.util.spec_from_file_location('_reviewed_public_chain',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
remote=module.REMOTE
start=remote.index("code=Path(");end=remote.index("sys.path.insert(0,str(code))")
remote=remote[:start]+'''root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
code=root/'runtime/aura'
raw=(root/'startup/config.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
pins=json.loads(raw)['component_sha256']
for relative in ('common/model_inference_wire.py','common/inference_output_contract.py',
 'board/runtime/board_dialogue_client.py','board/runtime/compact_request_adapter.py','common/board_timeline_clock.py'):
 assert hashlib.sha256((code/relative).read_bytes()).hexdigest()==pins[relative]
import subprocess
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit==dict(MainPID='0',ActiveState='inactive')
'''+remote[end:]

changes={
 "client=InferenceHttpClient('192.168.50.1',8797)": '''raw_client=InferenceHttpClient('192.168.50.1',8797)
from common.board_timeline_clock import StableTimelineClock
from tools.production_output_format import NegotiatedDialogueClient
cfg=json.loads((code/'config/board_avatar_gtk.json').read_bytes())['board_business']
timeline=StableTimelineClock(boot,raw_client.health_date_source_id(),raw_client.validate_sample,
 utc_bounds=cfg['utc_bounds'],monotonic=time.monotonic)
raw_client.sample_health_date(timeline,deadline=time.monotonic()+3)
client=NegotiatedDialogueClient(raw_client,system_prompt=prompt,mode=cfg['dialogue_output_format'])
assert client.public()['negotiated_dialogue_format']=='dialogue_abc_v1'
''',
 "response=client.request('llm',llm,deadline=deadline)": '''chain_start=time.monotonic()
response=client.request('llm',llm,deadline=deadline,cancelled=lambda:False)
llm_ms=(time.monotonic()-chain_start)*1000
llm_metrics={k:v for k,v in response.get('result',{}).get('metrics',{}).items() if type(v) in (int,float)}''',
 "response=client.request('tts',tts,deadline=deadline)": '''tts_start=time.monotonic()
response=client.request('tts',tts,deadline=deadline,cancelled=lambda:False)
tts_ms=(time.monotonic()-tts_start)*1000
model_chain_ms=(time.monotonic()-chain_start)*1000''',
 "public_reply=text.strip(),": "startup_sha256=EXPECTED,format_selection=client.public(),timings=dict(llm_ms=llm_ms,tts_ms=tts_ms,model_chain_ms=model_chain_ms,llm_metrics=llm_metrics),",
 "pcm_sha256=audio_sha,": "",
}
for old,new in changes.items():
    assert remote.count(old)==1
    remote=remote.replace(old,new)

if __name__=='__main__':
    output=HERE/'actual_public_compact_chain.json'
    assert not output.exists()
    installed=json.loads((HERE.parent.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    record,state=manage.latest();assert record and state['status']=='READY' and manage.same_owner(record)
    result=json.loads(ssh('python3 -B -','EXPECTED='+repr(installed['startup_sha256'])+'\n'+remote,timeout=90))
    after,after_state=manage.latest();assert after==record and after_state['pid']==state['pid'] and manage.same_owner(record)
    result['model_owner_binding']=dict(session_id=record['session_id'],host_pid=state['pid'],tts_pid=state['same_unique_tts_pid'])
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],timings=result['timings'],format_selection=result['format_selection'],audio_played=False)))
