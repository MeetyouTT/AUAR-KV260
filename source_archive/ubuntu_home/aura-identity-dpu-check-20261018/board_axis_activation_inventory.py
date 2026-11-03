"""Read exact activation inputs, with no register or model access."""
import base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
def output(args):return subprocess.check_output(args,text=True,timeout=6).strip()
camera=Path(output(['systemctl','show','aura-camera-ui.service','-p','WorkingDirectory','--value']))
gui=Path(output(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value']))
artifacts={}
for name,path in [('base-fdt.dtb',Path('/sys/firmware/fdt')),
 ('joint-payload-manifest.json',root/'payload_manifest.json'),
 ('joint-baseline-snapshot.json',root/'baseline-snapshot.json'),
 ('camera-unit.service',Path('/etc/systemd/system/aura-camera-ui.service')),
 ('active-camera-config.json',camera/'config/board_camera_ui.json')]:
 data=path.read_bytes();artifacts[name]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8790/v1/ui/status',timeout=2) as r:state=json.load(r)
identity=state.get('modules',{}).get('identity',{})
report={'status':'READ_ONLY_ACTIVATION_INPUTS','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera_root':str(camera),'gui_root':str(gui),'kernel_release':output(['uname','-r']),
 'identity_state':identity.get('state'),'identity_enrollment_in_progress':identity.get('state')=='ENROLLING',
 'camera_source_sha256':hashlib.sha256((camera/'board/vision/ui_camera_service.py').read_bytes()).hexdigest(),
 'staged_follow_source_present':Path('/home/root/aura-pan-follow-20261019/test-2f1e928a6ec30f9b/aura').is_dir(),
 'fdt_sha256':artifacts['base-fdt.dtb']['sha256'],'artifacts':artifacts}
print(json.dumps(report),flush=True)
