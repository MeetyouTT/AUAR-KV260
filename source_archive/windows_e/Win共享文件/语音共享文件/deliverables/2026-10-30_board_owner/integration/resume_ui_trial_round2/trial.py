"""One root-only entry; every inspection/action is a separate explicit step.

Default guard-inspect is metadata-only. This file is prepared locally, not
executed against a UI/service by its author. Only root publishes the trial.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import control_round2 as c
import launch_round2
import x11_close


def baseline(policy):
    expected=policy['baseline'];unit=c.show()
    c.need(unit['MainPID']==str(policy['old_supervisor']['pid']) and unit['ActiveState']=='active'
           and not unit.get('Job'),'reviewed_original_unit_required')
    c.need(c.same_owner(c.process(policy['old_supervisor']['pid']),policy['old_supervisor']) and
           c.same_owner(c.process(policy['old_child']['pid']),policy['old_child']),'original_owner_changed')
    c.need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id'],'boot_changed')
    camera=c.process(260102);c.need(camera and camera['birth']=='784437','camera_changed')
    c.need(c.digest(c.read(policy['startup']))==policy['startup_sha256'],'original_startup_changed')
    c.need(c.load(policy['startup'])['component_sha256']==policy['pins'],'original_pin_map_changed')
    for relative,sha in policy['pins'].items():
        c.need(c.digest(c.read(policy['runtime']+'/aura/'+relative,16777216))==sha,'original286_component_changed')
    c.need(c.digest(c.read(policy['launcher']))==policy['launcher_sha256'],'launcher_changed')
    for path,sha in expected['unit_source_sha256'].items():
        c.need(c.digest(c.read(path))==sha,'original_unit_source_changed')
    c.need(c.exec_argv(unit['ExecStart'])==c.exec_argv(expected['properties']['ExecStart']),'original_exec_changed')
    c.need(unit['DropInPaths']==expected['properties']['DropInPaths'],'original_dropins_changed')
    for key in ('Restart','SendSIGKILL','TimeoutStopUSec'):
        c.need(unit[key]==expected['properties'][key],'original_effective_properties_changed')
    state=c.safety(policy);c.need(state['ui_pid']==policy['old_supervisor']['pid'],'safety_ui_owner_changed')
    return unit,state


def guard_inspect(policy):
    unit,state=baseline(policy)
    paths=policy['baseline']['properties']['DropInPaths'].split()
    count=max([len(re.match(r'z*',Path(path).name).group()) for path in paths]+[0])+1
    name='z'*count+'-aura-yuki-capacity-20261030-r2.conf'
    c.need(len(name)<255 and all(Path(path).name<name for path in paths),'guard_sort_order')
    guard=str(Path(c.GUARD_ROOT)/name)
    c.need(not Path(c.CONTROL).exists() and not Path(guard).exists(),'round2_namespace_not_new')
    raw=b'[Service]\nRestart=no\nSendSIGKILL=no\nTimeoutStopSec=infinity\nKillSignal=SIGTERM\n'
    proof=dict(original_main_pid=policy['old_supervisor']['pid'],original_child_pid=policy['old_child']['pid'],
        owners=[policy['old_supervisor'],policy['old_child']],guard=guard,guard_sha256=c.digest(raw),
        source_sha256=policy['baseline']['unit_source_sha256'],state=state,
        original_exec=c.exec_argv(unit['ExecStart']),dropins=unit['DropInPaths'])
    return dict(status='GUARD_INSPECTED_NO_MUTATION',inspection_sha256=c.digest(c.encoded(proof)),
                guard=guard,source_pins=286,camera_pid=260102),proof,raw


def install_guard(policy,token):
    view,proof,raw=guard_inspect(policy)
    c.need(token==view['inspection_sha256'],'reviewed_guard_inspection_required')
    Path(c.CONTROL).mkdir(mode=0o700)
    folder=Path(c.GUARD_ROOT);folder.mkdir(mode=0o755,exist_ok=True)
    c.need(folder.resolve()==folder,'canonical_runtime_guard_directory_required')
    journal=dict(phase='GUARD_INTENT',unit=c.UNIT,guard=proof['guard'],guard_sha256=proof['guard_sha256'],
        original_properties=policy['baseline']['properties'],original_source_sha256=proof['source_sha256'],
        original_supervisor=policy['old_supervisor']['pid'],original_child=policy['old_child']['pid'],state=proof['state'])
    c.save(c.CONTROL+'/state.json',journal)
    fd=os.open(proof['guard'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    c.command(['/bin/systemctl','daemon-reload'],timeout=8)
    c.proof(policy);state=c.safety(policy)
    c.need(state==proof['state'],'safety_changed_during_guard_install')
    journal['phase']='GUARDED';c.save(c.CONTROL+'/state.json',journal)
    return dict(status='ROUND2_GUARDED_NO_UI_CLOSED',guard=proof['guard'],control=c.CONTROL)


def cancel_guard(policy):
    journal,unit=c.proof(policy)
    c.need(c.same_owner(c.process(policy['old_supervisor']['pid']),policy['old_supervisor']) and
           c.same_owner(c.process(policy['old_child']['pid']),policy['old_child']),'original_must_still_be_same_owner')
    c.need(c.candidate_owner() is None,'candidate_was_launched_restore_instead')
    state=c.safety(policy);c.need(state['ui_pid']==policy['old_supervisor']['pid'],'original_safety_owner_changed')
    Path(journal['guard']).unlink();c.command(['/bin/systemctl','daemon-reload'],timeout=8)
    after=c.show()
    for key in ('Restart','SendSIGKILL','TimeoutStopUSec','DropInPaths'):
        c.need(after[key]==journal['original_properties'][key],'original_properties_not_restored')
    c.need(c.safety(policy)==state,'safety_changed_during_guard_cancel')
    return dict(status='ONLY_ROUND2_GUARD_CANCELLED_ORIGINAL_UI_UNTOUCHED',main_pid=state['ui_pid'])


def window_plan(policy,candidate):
    plan=json.loads(c.read(Path(__file__).with_name('original_gui.plan.json')))
    if candidate:
        record=c.candidate_owner();c.need(record is not None,'candidate_owner_not_recorded')
        plan['owner']=record['owner']
        manifest=c.load(c.TARGET+'/assembly_manifest.json')
        sources={policy['launcher']:policy['launcher_sha256']}
        for relative in ('tools/board_avatar_pan.py','tools/board_avatar_gtk.py','tools/board_avatar_worker.py',
                         'tools/realtime_bridge.py','tools/native_yuki.py','tools/native_yuki_candidate.py',
                         'tools/yuki_business_candidate.py'):
            name='runtime/aura/'+relative
            sources[c.TARGET+'/'+name]=manifest['candidate_files'][name]['sha256']
        plan['sources']=sources
    return plan,c.digest(c.encoded(plan))


def inspect_or_close(policy,candidate,close,args):
    c.proof(policy)
    plan,sha=window_plan(policy,candidate)
    view=x11_close.X11(':0')
    try:
        if not close:return x11_close.inspect(plan,sha,x11_close.HostProof(),view)[0]
        c.need(args.review_token is not None and args.window_id is not None,'explicit_review_token_window_required')
        result=x11_close.request_close(plan,sha,x11_close.HostProof(),view,args.review_token,args.window_id)
        path=c.CONTROL+('/candidate_close.json' if candidate else '/original_close.json')
        c.save(path,result)
        result.update(receipt=path,receipt_sha256=c.digest(c.read(path)))
        return result
    finally:view.close()


def original_receipt():
    path=c.CONTROL+'/original_close.json';return path,c.digest(c.read(path))
def candidate_receipt(natural):
    if natural or c.candidate_owner() is None:return None,None
    path=c.CONTROL+'/candidate_close.json';return path,c.digest(c.read(path))


def main():
    steps=('guard-inspect','guard-install','guard-cancel','original-inspect','original-close',
           'launch-inspect','launch','candidate-inspect','candidate-close','restore-inspect','restore')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',nargs='?',choices=steps,default='guard-inspect')
    parser.add_argument('--policy',type=Path,default=Path(__file__).with_name('policy.json'))
    parser.add_argument('--policy-sha256',required=True)
    parser.add_argument('--inspection-sha256');parser.add_argument('--review-token')
    parser.add_argument('--window-id',type=lambda v:int(v,0));parser.add_argument('--candidate-exited-naturally',action='store_true')
    args=parser.parse_args()
    try:
        c.need(os.name=='posix' and os.geteuid()==0,'root_board_execution_only')
        policy=c.read_policy(args.policy,args.policy_sha256)
        if args.step=='guard-inspect':result=guard_inspect(policy)[0]
        elif args.step=='guard-install':result=install_guard(policy,args.inspection_sha256)
        elif args.step=='guard-cancel':result=cancel_guard(policy)
        elif args.step in ('original-inspect','original-close','candidate-inspect','candidate-close'):
            result=inspect_or_close(policy,args.step.startswith('candidate'),args.step.endswith('close'),args)
        elif args.step in ('launch-inspect','launch'):
            receipt,sha=original_receipt();result=launch_round2.launch(policy,receipt,sha,execute=args.step=='launch')
        else:
            receipt,sha=candidate_receipt(args.candidate_exited_naturally)
            result=c.restore(policy,receipt,sha,execute=args.step=='restore',
                             candidate_exited_naturally=args.candidate_exited_naturally)
        print(json.dumps(result));return 0
    except Exception as exc:
        print(json.dumps(dict(status='REFUSED_GUARD_RETAINED_NO_FORCE',error=type(exc).__name__+': '+str(exc),forced_action=False)))
        return 2


if __name__=='__main__':raise SystemExit(main())
