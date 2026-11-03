"""Verify an already healthy original UI after the bounded readiness wait."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SCRIPT=r'''
import hashlib,json,sys
from pathlib import Path
root='/home/root/aura-board-owner-candidate-20261030/ui-round2-4750fc97e43a75bd'
sys.path.insert(0,root);import control_round2 as c
assert hashlib.sha256(Path(root+'/control_round2.py').read_bytes()).hexdigest()=='c44451097a1ef9ac5cd6f1b0ccb72e316c054651b619a14c3b0b4ada7628337a'
policy=c.read_policy(root+'/policy.json','50f0c88ac736a153512afe022455b6e9925602620c9b332e4fb83e84a48dca18')
j,u=c.proof(policy)
assert u['MainPID']=='487238' and u['ActiveState']=='active' and not u.get('Job')
actual=c.process(487238);assert actual and actual['argv']==policy['old_supervisor']['argv']
child=c.process(487470);assert child and child['birth']=='1521602' and child['cmdline_sha256']=='0597ea080c70e32805da0dcb477a86edc8477345b48e9853c7dd05593223eb9f'
record=c.candidate_owner();assert record and c.owner_gone(record['owner']);c.candidate_tree_gone()
receipt=c.CONTROL+'/candidate_close.json';c.close_receipt(receipt,c.digest(c.read(receipt)),record['owner'])
before=c.safety(policy);assert before['ui_pid']==487238
guard=Path(j['guard']);assert c.digest(c.read(guard))==j['guard_sha256']
guard.unlink() # Only the exact private journal-owned runtime guard.
c.command(['/bin/systemctl','daemon-reload'],timeout=8)
final=c.show()
for key in ('Restart','SendSIGKILL','TimeoutStopUSec','DropInPaths'):
 assert final[key]==j['original_properties'][key]
assert final['MainPID']=='487238' and not final.get('Job')
assert c.exec_argv(final['ExecStart'])==c.exec_argv(j['original_properties']['ExecStart'])
after=c.safety(policy);assert before==after and c.same_owner(c.process(487238),actual) and c.same_owner(c.process(487470),child)
result=dict(status='ORIGINAL_VERIFIED_READY_AFTER_STARTUP_TIMEOUT_OWN_GUARD_REMOVED',main_pid=487238,gtk_pid=487470,camera_pid=260102,
 original_components_verified=286,original_startup_sha256=policy['startup_sha256'],normal_candidate_close=True,original_entry_unchanged=True,
 pan_state=after['pan_state'],pulse_us=after['pulse_us'],microphone_open=False,listening=False,following=False,playing=False,
 own_guard_removed=True,original_unit_properties_restored=True,other_service_action=False,forced_action=False)
c.save(c.CONTROL+'/restore_result.json',result)
print(json.dumps(result))
'''

def main():
    value=json.loads(ssh('python3 -B -',SCRIPT,timeout=25))
    target=HERE/'resume_ui_trial_round2/actual_restore_finalized.json';write_json(target,value)
    print(json.dumps(dict(output=str(target),**value)))

if __name__=='__main__':main()
