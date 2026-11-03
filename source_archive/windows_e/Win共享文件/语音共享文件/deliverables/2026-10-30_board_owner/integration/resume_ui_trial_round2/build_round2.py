"""Prepare isolated round2 source/policy from already captured public metadata."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'resume_ui_trial'
TARGET='/home/root/aura-board-owner-candidate-20261030/yuki-gui-capacity-20261030-r3'
CONTROL='/home/root/aura-board-owner-candidate-20261030/ui-capacity-control-20261030-r2'


def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Frozen integration point changed: '+old[:80])
    return source.replace(old,new,1)
def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    metadata=json.loads((ROOT/'actual_round2_metadata.json').read_text(encoding='utf-8'))
    launch=json.loads((ROOT/'actual_candidate_launch.json').read_text(encoding='utf-8'))
    original=json.loads((OLD/'actual_ui_baseline.json').read_text(encoding='utf-8'))
    policy=json.loads((OLD/'ui_trial_policy.v2.json').read_text(encoding='utf-8'))
    assert metadata['supervisor']['pid']==454995 and metadata['child']['pid']==455003
    assert metadata['original_pins']==286 and not metadata['original_component_changes'] and not metadata['original_alias_changes']
    assert launch['launch']['command'][2]==TARGET+'/runtime/aura/tools/board_avatar_pan.py' and launch['candidate_files']==356
    policy.update(round_revision=2,target=TARGET,old_supervisor=metadata['supervisor'],old_child=metadata['child'],
        baseline=metadata,inspection_sha256=launch['inspection'],
        launch_canonical_sha256=sha(json.dumps(launch['launch'],sort_keys=True,separators=(',',':')).encode()))
    source=(OLD/'restore_v2.py').read_text(encoding='utf-8')
    source=once(source,"TARGET=BASE+'/yuki-gui-capacity-20261030-r2'","TARGET=BASE+'/yuki-gui-capacity-20261030-r3'")
    source=once(source,"CONTROL=BASE+'/ui-capacity-control-20261030'","CONTROL=BASE+'/ui-capacity-control-20261030-r2'")
    source=once(source,"guard.name.endswith('-aura-yuki-capacity-20261030.conf')","guard.name.endswith('-aura-yuki-capacity-20261030-r2.conf')")
    (ROOT/'control_round2.py').write_text(source,encoding='utf-8')
    bridge=(OLD/'x11_normal_close_bin.py').read_text(encoding='utf-8').replace('1296','454995')
    bridge=once(bridge,'    after=host.static(plan)\n',
        "    while True:\n        try:\n            after=host.static(plan);break\n"
        "        except Refused as exc:\n"
        "            if str(exc)!='owner_changed' or clock()>=deadline:raise\n"
        "            wait(min(.1,max(0.,deadline-clock())))\n")
    (ROOT/'x11_close.py').write_text(bridge,encoding='utf-8')
    plan=json.loads((OLD/'original_gui.plan.json').read_text(encoding='utf-8'))
    plan.update(owner=dict(metadata['child'],parent_pid=454995),supervisor=metadata['supervisor'],boot_id=metadata['boot_id'])
    (ROOT/'original_gui.plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    launcher=original['launcher']['content'];assert sha(launcher.encode())==policy['launcher_sha256']
    tree=ast.parse(launcher);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_port_unused')
    function=''.join(launcher.splitlines(True)[node.lineno-1:node.end_lineno])
    (ROOT/'port_wait.py').write_text('"""Exact pinned original70second pre-spawn port guard; no call on import."""\nimport errno\nimport socket\nimport threading\nimport time\nSTOP=threading.Event()\n\n'+function,encoding='utf-8')
    candidate=(OLD/'launch_v2.py').read_text(encoding='utf-8')
    candidate=once(candidate,'import restore_v2 as control','import control_round2 as control\nfrom port_wait import check_port_unused')
    candidate=once(candidate,'        environment=dict(descriptor[\'environment\'],PATH=\'/usr/bin:/bin\',LANG=\'C.UTF-8\')',
        "        # Same pinned original pre-spawn guard, while the publisher flock is still held.\n"
        "        wait_started=time.monotonic()\n        check_port_unused(8783,wait_seconds=70)\n"
        "        control.inactive(policy)\n        control.candidate_tree_gone()\n"
        "        command=list(descriptor['command'])\n"
        "        evidence=control.CONTROL+'/evidence/gui-capacity-round2'\n"
        "        control.need(command.count('--evidence-root')==1,'one_reviewed_evidence_argument_required')\n"
        "        command[command.index('--evidence-root')+1]=evidence\n"
        "        environment=dict(descriptor['environment'],PATH='/usr/bin:/bin',LANG='C.UTF-8')")
    candidate=once(candidate,"child=subprocess.Popen(descriptor['command']",'child=subprocess.Popen(command')
    candidate=once(candidate,"owner['argv']==descriptor['command']","owner['argv']==command")
    candidate=once(candidate,"lock_lifetime='inherited FD held by GUI; released only on normal process exit')",
        "lock_lifetime='inherited FD held by GUI; released only on normal process exit',\n"
        "                      port_wait_seconds=time.monotonic()-wait_started,evidence_root=evidence)")
    (ROOT/'launch_round2.py').write_text(candidate,encoding='utf-8')
    (ROOT/'policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8')
    names=['trial.py','control_round2.py','launch_round2.py','port_wait.py','x11_close.py','policy.json','original_gui.plan.json']
    for name in names:
        if name.endswith('.py'):ast.parse((ROOT/name).read_bytes(),feature_version=(3,9))
    print(json.dumps(dict(status='ROUND2_SOURCE_BUILT_NOT_EXECUTED',target=TARGET,control=CONTROL,
        sha256={name:sha((ROOT/name).read_bytes()) for name in names})))


if __name__=='__main__':main()
