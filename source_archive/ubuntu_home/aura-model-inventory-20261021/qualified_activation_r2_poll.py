import json,subprocess
from pathlib import Path
p=Path('/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json')
d=json.loads(p.read_text()) if p.exists() else {}
out={k:d.get(k) for k in ('scope','phase','complete','passed','accepted','error','restore_error','metadata_warning',
    'release','qualified_report_sha256','source_manifest_sha256','unit_sha256','runtime_entry_sha256','handoff_root',
    'elapsed_s','observed_seconds','yolo_hz','yunet_hz','cpu_window','usb_warning_count','guard_state','guard_left_armed','restoration')}
out['sample_count']=len(d.get('samples',[]));out['latest_sample']=d.get('samples',[None])[-1] if d.get('samples') else None
out['units']={name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState'],timeout=5).decode().strip()
 for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
print(json.dumps(out,separators=(',',':')))
