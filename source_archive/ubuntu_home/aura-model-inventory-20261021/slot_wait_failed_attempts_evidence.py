import json,subprocess
from pathlib import Path
out={'read_only':True,'attempts':[]}
for key in ('a6a22198e4efd56b','05e856adcd70301b','9d649227aade936c'):
 root=Path('/home/root/aura-slot-wait-release-20261023')/key
 d=json.loads((root/'report.json').read_text())
 row={name:d.get(name) for name in ('scope','phase','complete','passed','accepted','error','error_location',
     'guard_left_armed','restore_error','recovery_after_rejection','release','handoff_root','timer')}
 row['helper_key']=key
 if d.get('fault_camera_snapshot'):
  h=d['fault_camera_snapshot'];f=h['face_targets'];s=h['dpu_schedule']
  row['fault']={'pid':h['pid'],'face_backend':f['backend'],'retry':f['slot_retry'],
   'yunet':s['optional']['yunet'],'recovery':s.get('yunet_recovery'),'slot_wait':s.get('yunet_slot_wait'),
   'freshness_counters':f['freshness_metrics']['counters'],'gap_records':f['freshness_metrics']['gap_records']}
 extra=root/'failed-trial-restoration.json'
 if extra.exists():row['independent_restoration']=json.loads(extra.read_text())
 out['attempts'].append(row)
names=['aura-slot-wait-baseline.service','aura-slot-wait-release-a6a22198e4efd56b.service',
 'aura-slot-wait-release-05e856adcd70301b.service','aura-slot-wait-release-9d649227aade936c.service',
 'aura-reject-slot-wait-9d649227.service','aura-slot-wait-release-restore-295705.timer']
out['old_auxiliary_states']={name:subprocess.check_output(['systemctl','show',name,'-p','ActiveState','--value'],timeout=4).decode().strip() for name in names}
print(json.dumps(out))
