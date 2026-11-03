from pathlib import Path
import json,subprocess
root=Path('/home/root/aura-dpu-vision-20261021');key='67ceb16087e7154a';unit='aura-postpower-long-'+key
launch=root/'postpower-long-launches'/key/'launch-result.json'
rows=sorted((root/'postpower-retry-live').glob('cbee206f503bab01-*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
status=subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','ExecMainPID','-p','Result','--no-pager'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True).stdout.strip()
journal=subprocess.run(['journalctl','-u',unit,'-n','8','--no-pager','-o','cat'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True).stdout.strip()
out={'launch':json.loads(launch.read_text()) if launch.exists() else None,'unit':status,'journal':journal}
if rows:
 p=rows[-1];d=json.loads(p.read_text());samples=d.get('samples',[])
 out['report_path']=str(p);out['summary']={k:d.get(k) for k in ('scope','passed','complete','phase','error','elapsed_s','observed_seconds','observed_yolo_hz','observed_yunet_hz','rollback_verified','rollback_error','usb_warning_count','sample_count','progress_checkpoint_bounded')}
 out['tail_sample']={k:samples[-1].get(k) for k in ('capture_hz','detection_hz','observation_age_ms','camera_error','detector_error','elapsed_s')} if samples else None
print(json.dumps(out,separators=(',',':')))
