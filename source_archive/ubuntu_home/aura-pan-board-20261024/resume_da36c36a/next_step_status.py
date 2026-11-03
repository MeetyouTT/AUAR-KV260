import json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan'];d=h['dpu_schedule']
launch=json.loads((R/'readonly-watch-launch.json').read_text());p=Path(launch['output'])
watch=json.loads((p/'status.json').read_text());rows=[json.loads(x) for x in (p/'samples.jsonl').read_text().splitlines()]
windows=[x for x in rows if 'kernel_window_s' in x]
print(json.dumps({'boot_id':boot,'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'camera_pid':h['pid'],'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'identity_ready':h['identity']['ready'],'owner_fenced':d['owner_fenced'],'detection_hz':h['detection_hz'],
 'primary_overruns':d['primary_period_overruns'],'optional_overruns':{k:v['overruns'] for k,v in d['optional'].items()},
 'manual_state':m['state'],'manual_error':m.get('error'),'automatic_following':m['automatic_following'],'readback':m.get('readback'),
 'audio_state':u['audio_output_state'],'ui_phase':u['phase'],'watch_status':watch['status'],'watch_reason':watch.get('reason'),
 'watch_elapsed_s':watch['elapsed_s'],'watch_samples':watch['samples'],'watch_errors':sum('error' in x for x in rows),
 'kernel_windows':len(windows),'sampled_usb_warnings':sum(x['xhci_buffer_warnings'] for x in windows),
 'capped_windows':sum(x['kernel_sample_capped'] for x in windows),'motor_commands':0,'MMIO_opened':False}))
