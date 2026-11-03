#!/usr/bin/env python3
"""Read camera/display/runtime inventory through the established board UART."""
import base64, datetime, gzip, importlib.util, json, shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out.mkdir(parents=True)
source=r'''
import json,os,subprocess,shutil
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def run(args):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
  return {'rc':p.returncode,'output':p.stdout[:16000]}
 except Exception as e:return {'error':str(e)}
videos={str(p):{'name':(p/'name').read_text().strip(),'device':str((p/'device').resolve())} for p in Path('/sys/class/video4linux').glob('video*')}
commands=[['xmutil','listapps'],['lsusb'],['v4l2-ctl','--list-devices'],['xrandr','--display',':0','--current'],['xset','-display',':0','q'],['systemctl','is-active','xserver-nodm'],['python3','-c','import cv2;print(cv2.__version__)']]
for p in sorted(Path('/dev').glob('video*')):commands.append(['v4l2-ctl','-d',str(p),'--list-formats-ext'])
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'video_devices':videos,'commands':{' '.join(a):run(a) for a in commands},'tools':{x:shutil.which(x) for x in ['gst-launch-1.0','gst-inspect-1.0','v4l2-ctl','ffplay','xdputil','python3']},'models':{str(p):[x.name for x in p.iterdir()] if p.exists() else [] for p in [Path('/usr/share/vitis_ai_library/models'),Path('/usr/share/vitis_ai_library/samples'),Path('/home/root/aura')]}}))
'''
(out/'remote.py').write_text(source)
spec=importlib.util.spec_from_file_location('uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with (out/'uart.raw').open('wb') as raw:
 u=mod.UART(raw)
 try:
  u.connect()
  payload=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
  code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(payload)+')))'
  rc,data,digest=u.command('python3 -B -c '+shlex.quote(code),'CAMERA_INVENTORY',100)
  (out/'result.json').write_bytes(data)
  print(data.decode())
  if rc:raise RuntimeError('Board inventory failed')
 finally: restored=u.close()
(ROOT/'CURRENT_INVENTORY.json').write_text(json.dumps({'evidence':str(out),'rc':rc,'sha256':digest,'console_echo_restored':restored},indent=2)+'\n')
