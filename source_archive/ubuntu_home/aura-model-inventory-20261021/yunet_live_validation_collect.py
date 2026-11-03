import json,subprocess,time,urllib.request
from pathlib import Path
out={'jobs':{},'units':{},'cu_statistics':{}}
base=Path('/home/root/aura-dpu-vision-20261021/live-validation')
for p in base.glob('*/progress.json'):
    value=json.loads(p.read_text());root=Path(value.get('root','/no-owned-root'))
    final=root/'deployment-result.json'
    if value.get('complete') and final.exists():value=json.loads(final.read_text())
    out['jobs'][str(p)]=value
    timer=value.get('timer')
    if timer:out['units'][timer+'.timer']=subprocess.check_output(['systemctl','show',timer+'.timer','-p','ActiveState'],timeout=3).decode().strip()
for n in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','systemd-journald.service']:
    out['units'][n]=subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip()
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto/stat')
first=cu.read_text();time.sleep(.4);second=cu.read_text()
out['cu_statistics']={'first':first.strip(),'second':second.strip(),'counter_frozen':first.split()[0]==second.split()[0]}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8790/health',timeout=3) as r:s=json.load(r)
out['final_camera']={k:s.get(k) for k in ['pid','capture_frames','detected_frames','capture_hz','detection_hz','camera_error','detector_error','observation_age_ms','dpu_schedule']}
out['final_camera']['identity_backend']=s.get('identity',{}).get('backend')
out['final_camera']['face_targets']=s.get('identity',{}).get('face_targets')
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as r:s=json.load(r)
out['final_ui']={k:s.get(k) for k in ['phase','playing','paused','audio_output_state']}
out['audio_pcm_status']=Path('/proc/asound/card1/pcm0p/sub0/status').read_text().strip()
print(json.dumps(out))
