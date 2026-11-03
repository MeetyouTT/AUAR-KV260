"""Root-owned frozen public chain, current board pause and Windows owner guards."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=REPAIR.parents[3]
sys.path[:0]=[str(PROJECT/'deliverables/2026-10-18_board_dialogue'),str(REPAIR.parent/'production_model_host')]
from board_ssh import ssh
import manage

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker-sha256',required=True);args=parser.parse_args()
    assert len(args.worker_sha256)==64 and all(x in '0123456789abcdef' for x in args.worker_sha256)
    worker=HERE/'public_chain/public_small_model_chain.py'
    raw=worker.read_bytes();assert hashlib.sha256(raw).hexdigest()==args.worker_sha256
    base_path=REPAIR/'frontend_allocation_candidate/public_probe/root_run_abba.py'
    module_spec=importlib.util.spec_from_file_location('_reviewed_public_slot_root',base_path)
    base=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(base)
    stage='/home/root/aura-public-small-chain-20261031/'+args.worker_sha256[:16]
    old='/home/root/aura-public-frontend-allocation-20261031/c7988d2439fbb0d7'
    assert base.REMOTE.count(old)==1
    remote=base.REMOTE.replace(old,stage).replace('asr_called=False','asr_worker_requested=True')
    installed=json.loads((REPAIR.parent/'production_business_acceptance/spec.json').read_bytes())
    assert installed['startup_sha256']=='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
    record,state=manage.latest();assert record and state['status']=='READY' and manage.same_owner(record)
    health=manage.health();backend=health['backend']
    assert health['ok'] is True and health['role']=='model_inference_only' and health['request_logging'] is False
    assert backend['model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and backend['tts']=='omnivoice'
    assert backend['num_step']==16 and backend['tts_ready'] is True and backend['gpu_coordination']['enforcing'] is True
    # Board-side guard waits for an idle gap; no production cancellation/pause change.
    bound=dict(session_id=record['session_id'],host_pid=state['pid'],tts_pid=state['same_unique_tts_pid'],ollama_pid=state['fixed_daemon_pid'])
    values=dict(STAGE=stage,FILES=[dict(relative_path=worker.name,bytes=len(raw),sha256=args.worker_sha256,base64=base64.b64encode(raw).decode())],
                BOOT=installed['boot_id'],EXPECTED=installed['startup_sha256'],SLOT='public-small-model-chain',ARM='v16',
                ARGV=['timeout','--signal=TERM','--kill-after=5s','80s','/usr/bin/python3','-B','-s',stage+'/'+worker.name,'--external-deadline-managed'])
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+remote,timeout=125))
    after,after_state=manage.latest()
    same=bool(after==record and manage.same_owner(record) and after_state['pid']==bound['host_pid'] and after_state['same_unique_tts_pid']==bound['tts_pid'] and after_state['fixed_daemon_pid']==bound['ollama_pid'])
    result.update(model_owner_binding=bound,model_owners_unchanged=same,worker_sha256=args.worker_sha256,
                  root_runner_sha256=sha(Path(__file__)),root_guard_source_sha256=sha(base_path))
    out=HERE/'public_chain'/('ACTUAL_CHAIN_'+str(time.time_ns())+'.json')
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(out),status=result['result'].get('status'),exit_code=result['exit_code'],
        elapsed_seconds=result['elapsed_seconds'],manual_pause_preserved=result['manual_pause_preserved'],
        model_owners_unchanged=same,background_activity_changed=result['background_activity_changed'])))
    if not same:raise RuntimeError('model_owner_changed_evidence_retained')
