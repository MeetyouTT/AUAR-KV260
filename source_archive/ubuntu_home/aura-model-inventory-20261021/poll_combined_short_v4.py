from pathlib import Path
import json
root=Path('/home/root/aura-dpu-vision-20261021')
key='ad0e90471ce14261'
launch=root/'postpower-combined-launches'/key/'launch-result.json'
rows=sorted((root/'postpower-retry-live').glob('cbee206f503bab01-*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
out={'launch':json.loads(launch.read_text()) if launch.exists() else None}
if rows:
 p=rows[-1];d=json.loads(p.read_text());out['report_path']=str(p)
 out['summary']={k:d.get(k) for k in ('scope','passed','complete','phase','error','elapsed_s','observed_seconds','observed_yolo_hz','observed_yunet_hz','rollback_verified','rollback_error','usb_warning_count')}
 out['optional']=d.get('optional');out['face']=d.get('face');out['cpu_window']=d.get('cpu_window');out['faults']=d.get('faults')
print(json.dumps(out,separators=(',',':')))
