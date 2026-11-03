"""Repair the exact first-attempt keyword error, preserving both transaction histories."""
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parents[3]/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
    root=HERE/'package/original_direction_fix'
    plan=json.loads((root/'plan.json').read_bytes())
    first=json.loads((HERE/'package/original_restore/plan.json').read_bytes())
    common=(HERE/'remote/_session_common.py').read_text(encoding='utf-8')
    source=common+'\nPLAN='+repr(plan)+'\nFIRST='+repr(first)+'''\n
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert systemd()['MainPID']==str(state()['restored_camera_pid'])
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState','--no-pager'],capture_output=True,text=True,timeout=5)
assert 'MainPID=0' in unit.stdout and 'ActiveState=inactive' in unit.stdout
pub=Path('/home/root/aura-board-business-20261030/control-production-v1/state.json')
current=document(pub);before=document(Path(PLAN['stage'])/'before/publication-state.json')
assert current['phase']=='AXIS_ORIGINAL_BINDING_INTENT' and before['phase']=='NORMAL_CLOSED'
assert 'axis_direction_rebind' not in current
wrong=current['axis_original_rebind']
assert wrong['state']=='INTENT' and wrong['stage']==PLAN['stage'] and wrong['transaction_sha256']==PLAN['transaction_sha256']
old=before['axis_original_rebind']
assert old['state']=='APPLIED' and old['stage']==FIRST['stage'] and old['transaction_sha256']==FIRST['transaction_sha256']
assert digest(Path(FIRST['stage'])/'transaction.json')==FIRST['transaction_sha256']
assert digest(Path(PLAN['stage'])/'transaction.json')==PLAN['transaction_sha256']
expected=dict(before,phase='AXIS_ORIGINAL_BINDING_INTENT',axis_original_rebind=wrong)
assert current==expected
for row in PLAN['targets'].values():assert digest(row['path'])==row['new_sha256']
atomic(Path(PLAN['stage'])/'misnamed-marker-failure.json',current)
current['axis_direction_rebind']=wrong;current['axis_original_rebind']=old
atomic(pub,current)
print(json.dumps(dict(status='EXACT_DIRECTION_INTENT_MARKER_REPAIRED',old_history_preserved=True,
 configuration_payloads_changed=False,all_configuration_targets_already_exact_new=True,
 failed_journal_sha256=digest(Path(PLAN['stage'])/'misnamed-marker-failure.json'),
 repaired_journal_sha256=digest(pub),gui_inactive=True,motion_commands_sent=0)))
'''
    result=json.loads(ssh('python3 -B -',source,timeout=20))
    output=HERE/'evidence'/('direction_marker_repair_'+str(time.time_ns())+'.json')
    output.write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),result=result),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(evidence=str(output),result=result)))

if __name__=='__main__':main()
