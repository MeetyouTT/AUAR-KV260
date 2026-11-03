import fcntl,hashlib,json,os,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
legacy=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb')
candidate=Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9')
config=json.loads((legacy/'board_camera_ui.json').read_text())
tracking=config['tracking'];identity=json.loads(Path(config['identity']['config']).read_text())
files={}
for name,digest in tracking['source_sha256'].items():
 p=legacy/'aura/board/vision/bytetrack'/name
 files[name]={'exists':p.exists(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,'expected':digest}
markers=[str(p) for p in (candidate/'state').rglob('*') if p.is_file()]
lock=open('/run/aura-person-dpu.lock','a+');held=False
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);held=True
except BlockingIOError:pass
lock.close()
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'tracking':tracking,'tracking_files':files,'identity_paths':{k:v for k,v in identity.items() if isinstance(v,str) and v.startswith('/')},
 'candidate_state_files':markers,'dpu_lock_confirmed_free':held,
 'state':json.loads((root/'state.json').read_text()),
 'camera':subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus'],text=True)}))
