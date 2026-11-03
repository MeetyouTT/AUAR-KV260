import json,subprocess
from pathlib import Path
keys=('7b0f63f00dd263f7','36accddbc2be2cd8','30072c67abc3f06b','cfcba65b98ee2a2b',
      '67f93c97570180fe','1171f852973b2a1c','d8f274b01ce71e78')
out={'read_only':True,'attempts':[]}
for key in keys:
 p=Path('/home/root/aura-sface-formal-20261023')/key/'report.json';d=json.loads(p.read_text())
 row={k:d.get(k) for k in ('phase','complete','passed','accepted','error','error_location','restore_error',
      'guard_left_armed','restoration','migration','release','timer')};row['helper_key']=key
 row['stages']=[{k:s.get(k) for k in ('observed_seconds','yolo_hz','face_publish_hz','sface_hz',
    'sface_native_completed_delta','known_correct_samples','known_decision_fraction','cpu_window','usb_warning_count')} for s in d.get('stages',[])]
 row['controller_state']=subprocess.check_output(['systemctl','show','aura-sface-formal-'+key+'.service','-p','ActiveState','--value'],timeout=3).decode().strip()
 if d.get('timer'):row['restore_timer_state']=subprocess.check_output(['systemctl','show',d['timer']+'.timer','-p','ActiveState','--value'],timeout=3).decode().strip()
 out['attempts'].append(row)
print(json.dumps(out))
