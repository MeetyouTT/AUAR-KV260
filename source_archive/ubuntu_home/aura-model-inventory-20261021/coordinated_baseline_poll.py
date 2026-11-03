import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-coordinated-switch-20261023/eb4e29a1b9ea9737')
path=root/'report.json';d=json.loads(path.read_text()) if path.exists() else {}
out={k:d.get(k) for k in ('scope','phase','complete','passed','error','elapsed_s','observed_seconds',
                          'yolo_hz','yunet_hz','cpu_window','usb_warning_count','restore_error','restoration','guard_left_armed')}
out['sample_count']=len(d.get('samples',[]))
out['latest_sample']=d.get('samples',[None])[-1] if d.get('samples') else None
out['units']={name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState'],timeout=5).decode().strip()
              for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
print(json.dumps(out,separators=(',',':')))
