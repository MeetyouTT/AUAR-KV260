"""Prepare an inspectable original-GTK proof from existing local root evidence."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ORIGINAL='/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu'


def main():
    baseline=json.loads((ROOT/'actual_ui_baseline.json').read_text(encoding='utf-8'))
    fresh=json.loads((ROOT.parent/'resume_runtime/fresh_source/manifest.json').read_text(encoding='utf-8'))
    launcher=baseline['launcher']['content'].encode()
    if hashlib.sha256(launcher).hexdigest()!=baseline['launcher']['sha256']:raise ValueError('Launcher source mismatch')
    def owner(row):
        return dict(pid=row['pid'],birth=row['birth'],argv=row['argv'],
            cmdline_sha256=hashlib.sha256(('\0'.join(row['argv'])+'\0').encode()).hexdigest())
    target=owner(baseline['children'][0]);target['parent_pid']=baseline['pid']
    sources={baseline['launcher']['path']:baseline['launcher']['sha256']}
    for relative in ('tools/board_avatar_pan.py','tools/board_avatar_gtk.py','tools/board_avatar_worker.py',
                     'tools/board_recording.py','tools/realtime_audio.py','tools/streaming_controller.py'):
        sources[ORIGINAL+'/runtime/aura/'+relative]=fresh['source_sha256'][relative]
    plan=dict(schema_version=1,unit='aura-avatar-ui.service',display=':0',boot_id=fresh['boot'],
              owner=target,supervisor=owner(baseline),sources=sources)
    raw=json.dumps(plan,indent=2).encode();(ROOT/'original_gui.plan.json').write_bytes(raw)
    tree=ast.parse(launcher)
    supervise=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='supervise')
    pops=sum(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='Popen' for node in ast.walk(supervise))
    review=dict(schema_version=1,launcher_sha256=baseline['launcher']['sha256'],source_content_sha_match=True,
        supervise_popen_calls=pops,internal_respawn_loop=False,
        normal_child_exit='child.poll()!=None returns; finally stop_child immediately returns when child already exited',
        critical='Do not TERM or systemctl stop supervisor first: stop_child includes child.terminate then child.kill timeout. Outer SendSIGKILL=no does not disable that Python path.',
        systemd_restart='Effective Restart=no prevents unit restart after natural supervisor exit',
        required_effective_guards=dict(Restart='no',SendSIGKILL='no',TimeoutStopUSec='infinity',MainPID=['1296','0']),
        no_actual_actions_performed=True,plan_sha256=hashlib.sha256(raw).hexdigest())
    (ROOT/'launcher_review.json').write_text(json.dumps(review,indent=2),encoding='utf-8')
    print(json.dumps(dict(plan='original_gui.plan.json',plan_sha256=review['plan_sha256'],owner_pid=target['pid'],
                          owner_birth=target['birth'],cmdline_sha256=target['cmdline_sha256'],launcher_popen_calls=pops)))


if __name__=='__main__':main()
