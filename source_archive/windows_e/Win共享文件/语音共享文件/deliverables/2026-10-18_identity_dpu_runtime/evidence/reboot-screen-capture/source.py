import base64,hashlib,json,os,subprocess,tempfile
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
env=dict(os.environ,DISPLAY=':0')
def run(args,timeout=5):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env,timeout=timeout)
  return {'returncode':p.returncode,'output':p.stdout[-7000:]}
 except Exception as exc:return {'error':str(exc)}
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
out={'status':'READ_ONLY_DISPLAY','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0]}
out['display']=run(['xrandr','--current'])
edid=Path('/sys/class/drm/card0-DP-1/edid');out['edid_bytes']=edid.stat().st_size if edid.exists() else None
out['kernel_errors']=run(['journalctl','-k','-p','err','-n','12','--no-pager','-o','cat'])
marker=Path('/run/aura-display-startup.json')
out['startup_display_marker']=json.loads(marker.read_text()) if marker.exists() else None
out['activation_result_exists']=(root/'activation-final-result.json').exists()
working=run(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'])
aura=Path(working.get('output','').strip());out['ui_working_directory']=str(aura)
if aura in (root/'candidate/runtime/aura',Path('/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/runtime/aura')):
 with tempfile.TemporaryDirectory(prefix='aura-display-read-') as folder:
  png=Path(folder)/'screen.png'
  shot=run(['python3','-B',str(aura/'tools/board_screen_capture.py'),str(png)],8)
  out['capture']=shot
  if png.exists():
   from PIL import Image
   jpeg=Path(folder)/'screen.jpg'
   with Image.open(png) as source:
    out['screen_dimensions']=list(source.size);source.convert('RGB').save(jpeg,format='JPEG',quality=75)
   data=jpeg.read_bytes();assert len(data)<140000
   out['artifacts']={'screen.jpg':{'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}
print(json.dumps(out),flush=True)
