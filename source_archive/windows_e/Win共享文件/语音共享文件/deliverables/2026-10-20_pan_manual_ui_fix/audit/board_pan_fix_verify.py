"""Read-only final source/platform/camera and process-owner verification."""
import base64,gzip,hashlib,json,subprocess,time,urllib.request
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/fix-v2');payload=json.loads((p/'payload.json').read_text());root=Path(payload['baseline']['aura_root'])
original=json.loads(Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/startup/config.json').read_text())
for rel,sha in original['component_sha256'].items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==sha,rel
for rel,item in payload['files'].items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==item['sha256'],rel
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=1) as r:return json.load(r)
s=get(8783,'/api/state');pan=s['manual_pan'];assert pan['state']=='READY' and pan['readback']['flags']==0 and pan['readback']['lease_left_ms']==0
camera=get(8790,'/health');assert camera['pid']==106060 and not camera['camera_error'] and not camera['detector_error']
launch=json.loads((root.parent/'launch.json').read_text());gui_pid=launch['pid'];backend=pan['backend_pid'];assert gui_pid!=backend
status=(Path('/proc')/str(backend)/'status').read_text();ppid=int(next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('PPid:')));assert ppid==gui_pid
reg=json.loads((p/'regression.json').read_text());assert reg['status']=='UI_COARSE_FINE_RECONNECT_PASS_FINAL1450_OUTPUT_OFF'
report={'status':'FINAL_READ_ONLY_PASS','original_components_unchanged':len(original['component_sha256']),'new_files_verified':len(payload['files']),
 'gui_pid':gui_pid,'backend_pid':backend,'backend_ppid':ppid,'ui_phase':s['phase'],'ui_page':s['ui_page'],'manual_pan':pan,
 'camera':{k:camera.get(k) for k in ['pid','detection_hz','identity_recognition','camera_error','detector_error']},
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'vart':Path('/etc/vart.conf').read_text().strip(),
 'display_retrain_off_seconds':json.loads((p/'startup/config.json').read_text())['display_retrain_off_seconds']}
print(json.dumps(report),flush=True)
