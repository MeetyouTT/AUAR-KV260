
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

driver=Path('/sys/bus/i2c/drivers/usb5744')
dev=Path('/sys/bus/i2c/devices/1-002d')
assert dev.joinpath('name').read_text().strip()=='usb5744'
assert dev.joinpath('driver').resolve()==driver
assert not list(Path('/sys/class/video4linux').glob('video*'))
assert sorted(x.name for x in Path('/sys/bus/usb/devices').iterdir() if x.name[0].isdigit())==['1-0:1.0','2-0:1.0']
before=run(['lsusb','-t'])
driver.joinpath('unbind').write_text('1-002d')
try:
 driver.joinpath('bind').write_text('1-002d')
finally:
 if not dev.joinpath('driver').exists():
  try:driver.joinpath('bind').write_text('1-002d')
  except Exception as e:print('Driver restore failed:',str(e))
import time
time.sleep(3)
commands=[['lsusb','-t'],['lsusb'],['v4l2-ctl','--list-devices'],['sh','-c',"dmesg | grep -Ei 'usb|uvc|hub' | tail -35"]]

for p in sorted(Path('/dev').glob('video*')):commands.append(['v4l2-ctl','-d',str(p),'--list-formats-ext'])
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'video_devices':videos,'commands':{' '.join(a):run(a) for a in commands},'tools':{x:shutil.which(x) for x in ['gst-launch-1.0','gst-inspect-1.0','v4l2-ctl','ffplay','xdputil','python3']},'models':{str(p):[x.name for x in p.iterdir()] if p.exists() else [] for p in [Path('/usr/share/vitis_ai_library/models'),Path('/usr/share/vitis_ai_library/samples'),Path('/home/root/aura')]}}))
