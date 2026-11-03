import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as stream:return json.load(stream)
h=get(8790,'/health');s=h['dpu_schedule']
units={}
for name in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
 p=subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','MainPID','-p','NRestarts','-p','Restart','-p','ExecStart','-p','After','-p','Requires','-p','Wants','-p','WorkingDirectory','-p','Type'],text=True)
 units[name]=dict(line.split('=',1) for line in p.splitlines() if '=' in line)
source=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb')
config=json.loads((source/'board_camera_ui.json').read_text())
identity=Path(config['identity']['config'])
if not identity.is_absolute():identity=(source/'aura'/identity).resolve()
cfg=json.loads(identity.read_text())
gui=get(8783,'/api/state')
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'camera':{'pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':s['optional'],'owner_fenced':s['owner_fenced'],
 'primary_calls':s['primary_calls'],'primary_overruns':s['primary_period_overruns'],'yunet_recovery':s['yunet_recovery'],
 'sface_recovery':s['sface_recovery'],'feature_inference':h['identity']['feature_inference']},
 'units':units,'camera_unit_text':subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True),
 'gui_summary':{k:gui.get(k) for k in ['phase','audio_output_state','ui_page','paused','playing']},
 'yolo_config':config['yolo'],'face_backends':{k:cfg[k] for k in ['face_backend','feature_backend']},
 'yunet_ttl_ms':cfg.get('face_target_ttl_ms'),'inference_fps':config['inference_fps'],
 'launcher_source':(source/'gil_camera_launcher.py').read_text(),
 'config_sha256':hashlib.sha256((source/'board_camera_ui.json').read_bytes()).hexdigest(),
 'identity_config_sha256':hashlib.sha256(identity.read_bytes()).hexdigest()}))
