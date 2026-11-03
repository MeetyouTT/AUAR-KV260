"""Read-only production metadata and exact source-map discovery; no content export."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib,http.client,json,pathlib,subprocess
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 c.request('GET','/api/state');r=c.getresponse();raw=r.read(1048577)
 assert r.status==200 and len(raw)<=1048576
 state=json.loads(raw)
finally:c.close()
def shape(value,depth=2):
 if not isinstance(value,dict):return type(value).__name__
 return {k:shape(v,depth-1) if depth>0 and isinstance(v,dict) else type(v).__name__ for k,v in value.items()}
startup_raw=(root/'startup/config.json').read_bytes();startup=json.loads(startup_raw)
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
keys=('handsfree_dialogue','board_business','board_processing','local_recording','local_transcription','last_job','metrics','streaming_reply','audio_output_state')
out=dict(unit=unit,root=str(root),startup_sha256=hashlib.sha256(startup_raw).hexdigest(),
 board_boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 top_keys=sorted(state),schema={k:shape(state[k]) for k in keys if k in state},
 listening={k:state.get('handsfree_dialogue',{}).get(k) for k in ('enabled','state','microphone_open','conversation_entered')},
 task_state=state.get('board_processing',{}).get('task_state'),
 memory={k:state.get('board_business',{}).get('memory',{}).get(k) for k in ('running','completed','discarded','model_calls_inside_transaction')},
 memory_error_code=(state.get('board_business',{}).get('memory',{}).get('error') if state.get('board_business',{}).get('memory',{}).get('error') in ('','cancelled','candidate_rejected','database_busy','model_failed','clock_unverified') else 'other'),
 diagnostics=state.get('safe_capture_diagnostics',{}),playing=state.get('playing'),
 source_pins={k:v for k,v in startup['component_sha256'].items() if any(t in k for t in ('board_business','board_asr','board_dialogue','speaker','model_client','inference','endpoint','thinking','recording')) and k.endswith('.py')})
print(json.dumps(out))
'''

if __name__ == '__main__':
    value=json.loads(ssh('python3 -B -',REMOTE,timeout=20))
    (HERE/'board_baseline.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value,ensure_ascii=True))
