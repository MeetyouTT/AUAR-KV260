"""Root-only public feature wording probe over the allowed board Ethernet peer."""
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

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker-sha256',required=True);args=parser.parse_args()
    assert len(args.worker_sha256)==64 and all(x in '0123456789abcdef' for x in args.worker_sha256)
    worker=HERE/'public_board_probe_v2/worker.py'
    entries=[('worker.py',worker,args.worker_sha256),
        ('source_mapping.json',REPAIR/'paraformer_small_validation/v16_evidence/source_mapping.json','c56a5920d55ca99cbe46680a6d5fffd3174e00bb09c7dae52084ce7de0f5640b'),
        ('V16_SOURCE_VERIFICATION.json',HERE/'V16_SOURCE_VERIFICATION.json','37c2dc75fdc3c41be6cba6bc0a27f26e242d259a9043febbe530945387d3d0c0')]
    files=[]
    for rel,path,pin in entries:
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
        files.append(dict(relative_path=rel,sha256=pin,bytes=len(raw),base64=base64.b64encode(raw).decode()))
    base_path=REPAIR/'frontend_allocation_candidate/public_probe/root_run_abba.py'
    spec=importlib.util.spec_from_file_location('_reviewed_root_slot',base_path)
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    stage='/home/root/aura-public-feature-grounding-20261031/'+args.worker_sha256[:16]
    old='/home/root/aura-public-frontend-allocation-20261031/c7988d2439fbb0d7'
    assert base.REMOTE.count(old)==1 and base.REMOTE.count('timeout=85')==1
    remote=base.REMOTE.replace(old,stage).replace('timeout=85','timeout=270')
    installed=json.loads((REPAIR.parent/'production_business_acceptance/spec.json').read_bytes())
    assert installed['startup_sha256']=='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
    record,state=manage.latest();assert record and state['status']=='READY' and manage.same_owner(record)
    h=manage.health();b=h['backend']
    assert h['ok'] and h['request_logging'] is False and h['role']=='model_inference_only'
    assert b['model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and b['tts']=='omnivoice' and b['num_step']==16
    assert b['gpu_coordination']['enforcing'] is True
    bound=dict(session_id=record['session_id'],host_pid=state['pid'],tts_pid=state['same_unique_tts_pid'],ollama_pid=state['fixed_daemon_pid'])
    root='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
    values=dict(STAGE=stage,FILES=files,BOOT=installed['boot_id'],EXPECTED=installed['startup_sha256'],
        SLOT='public-feature-grounding-v2',ARM='v16',ARGV=[
        'timeout','--signal=TERM','--kill-after=5s','260s','/usr/bin/python3','-B','-s',stage+'/worker.py',
        '--coordinated-slot','root-feature-grounding-v2','--runtime-root',root+'/runtime/aura',
        '--startup-config',root+'/startup/config.json','--output',stage+'/PUBLIC_MODEL_GROUNDING_BOARD_V2.json'])
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+remote,timeout=310))
    after,after_state=manage.latest()
    same=bool(after==record and manage.same_owner(record) and after_state['pid']==bound['host_pid'] and after_state['same_unique_tts_pid']==bound['tts_pid'] and after_state['fixed_daemon_pid']==bound['ollama_pid'])
    result.update(model_owner_binding=bound,model_owners_unchanged=same,worker_sha256=args.worker_sha256,
        source_peer='192.168.50.2',production_access_policy_changed=False,
        root_runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    output=HERE/('PUBLIC_BOARD_GROUNDING_ACTUAL_'+str(time.time_ns())+'.json')
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(output),status=result['result'].get('status'),exit_code=result['exit_code'],
        elapsed_seconds=result['elapsed_seconds'],manual_pause_preserved=result['manual_pause_preserved'],
        model_owners_unchanged=same,background_activity_changed=result['background_activity_changed'])))
    if not same:raise RuntimeError('model_owner_changed_evidence_saved')
