import hashlib,json,subprocess,urllib.request
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unit(name):
 p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,NRestarts,FragmentPath,DropInPaths'],capture_output=True,text=True)
 d=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
 d['file_sha256']={n:sha(n) for n in [d['FragmentPath']]+d.get('DropInPaths','').split() if n}
 return d
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as response:h=json.load(response)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as response:g=json.load(response)
config=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/config.json')
launcher=config.with_name('launcher.py')
result={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'fdt_sha256':sha('/sys/firmware/fdt'),
 'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'gui_unit':unit('aura-avatar-ui.service'),'camera_unit':unit('aura-camera-ui.service'),
 'launcher_path':str(launcher),'launcher_sha256':sha(launcher),'startup_config_path':str(config),'startup_config_sha256':sha(config),
 'startup_config':json.loads(config.read_text()),'camera_pid':h['pid'],'native_critical':h['dpu_schedule']['native_critical'],
 'owner_fenced':h['dpu_schedule']['owner_fenced'],'gui':{k:g.get(k) for k in ['phase','audio_output_state','playing']},
 'local_recording_state':g.get('local_recording',{}).get('state'),
 'camera_config_path':'/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/board_camera_ui.proposed.json'}
result['camera_config_sha256']=sha(result['camera_config_path'])
print(json.dumps(result))
