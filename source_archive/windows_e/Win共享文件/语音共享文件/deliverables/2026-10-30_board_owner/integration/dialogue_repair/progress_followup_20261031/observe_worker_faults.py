"""Low-frequency numeric observation of the newly instrumented render worker."""
import argparse
import json
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import probe

EXTRA=r'''
renderer=state.get('avatar_renderer',{})
fault=renderer.get('worker_faults',{})
out['renderer_worker_faults']=runtime_faults(fault)
last=fault.get('last') or {}
out['renderer_worker_fault_detail']={k:last.get(k) for k in ('observed_mono','sequence','generation') if type(last.get(k)) in (int,float)}
out['renderer_worker_fault_detail']['stage']=last.get('stage') if last.get('stage') in ('tick','frame','state_snapshot','publication') else None
tid=renderer.get('worker_native_tid')
out['renderer_worker_native_tid']=tid if type(tid) is int and tid>0 else None
for key in ('ui_stage_timings_ms','ui_runtime_timings_ms','ui_settings_timings_ms','ui_callback_previous','ui_widget_writes'):
 out[key]=scalar(state.get(key,{}))
reason=h.get('reason')
out['listening_reason']=reason if reason in ('CURRENT_TURN_CANCELLED','CONVERSATION_SILENCE','SPEECH_ACCEPTED','DIRECT_SPEECH','USER_PAUSED') else 'other'
print(json.dumps(out),flush=True)
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-startup',required=True)
    parser.add_argument('--samples',type=int,default=40)
    parser.add_argument('--interval',type=int,default=3)
    args=parser.parse_args()
    assert len(args.expected_startup)==64 and all(x in '0123456789abcdef' for x in args.expected_startup)
    assert 1<=args.samples<=60 and 2<=args.interval<=10
    source=probe.REMOTE.replace('print(json.dumps(out))',EXTRA)
    remote=('import time\nSOURCE='+repr(source)+'\nEXPECTED='+repr(args.expected_startup)+'\n'
            +'for _ in range('+str(args.samples)+'):\n exec(SOURCE)\n'
            +' if out["startup_sha256"]!=EXPECTED:raise RuntimeError("OBSERVATION_SOURCE_CHANGED")\n'
            +' if out["renderer_worker_faults"]["count"]>0:break\n'
            +' time.sleep('+str(args.interval)+')\n')
    rows=[json.loads(line) for line in probe.ssh('python3 -B -',remote,timeout=args.samples*(args.interval+1)+15).splitlines() if line.strip()]
    path=HERE/('worker_observation_'+str(time.time_ns())+'.json')
    path.write_text(json.dumps({'samples':rows,'interval_seconds':args.interval,'private_text_exported':False},indent=2)+'\n',encoding='utf8')
    latest=rows[-1]
    print(json.dumps({'file':str(path),'samples':len(rows),**{key:latest[key] for key in (
        'observed_mono','phase','listening','renderer_worker_faults','renderer_worker_fault_detail','renderer_worker_native_tid','native')}}))
