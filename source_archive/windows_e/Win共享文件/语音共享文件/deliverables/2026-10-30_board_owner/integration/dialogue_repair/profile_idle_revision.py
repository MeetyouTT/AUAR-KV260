"""Reuse the read-only CPU profile with same-window native frame counters."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import profile_board_budget as baseline
from board_ssh import ssh

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('label')
    args=parser.parse_args()
    assert args.label.replace('_','').isalnum()
    old=" return dict(at=time.monotonic(),processes=result,cpus=cpus,gauges=gauges,state=state_meta)"
    new=""" state_meta['native']={k:state.get('avatar_display',{}).get(k) for k in ('frames','target_fps','visible','gtk_callback_ms')}
 state_meta['ipc']={k:state.get('audio_output',{}).get('ipc',{}).get(k) for k in ('blocked_writes','coalesced_states','pending_bytes')}
 return dict(at=time.monotonic(),processes=result,cpus=cpus,gauges=gauges,state=state_meta)"""
    assert baseline.REMOTE.count(old)==1
    script=baseline.REMOTE.replace(old,new)
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    live=json.loads((HERE.parent/'listening_entry_fix/actual_live_listening.json').read_text(encoding='utf-8'))
    result=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\nCAMERA='+repr(live['camera_pid'])+'\n'+script,timeout=30))
    first=result['state_before']['native']['frames']
    last=result['state_after']['native']['frames']
    result['observed_native_fps']=(last-first)/result['duration_seconds'] if type(first) is int and type(last) is int and last>=first else None
    result['sampler_source_sha256']=hashlib.sha256(script.encode()).hexdigest()
    (HERE/(args.label+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cpu=result['cpu']['cpu'],native_fps=result['observed_native_fps'],
        state_before=result['state_before'],state_after=result['state_after'],
        roles=[{k:r[k] for k in ('pid','role','cpu_core_percent')} for r in result['processes']])))
