
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
commands=[['lsusb','-t'],['sh','-c',"dmesg | grep -Ei 'usb|xhci|uvc|video' | tail -100"],['sh','-c',"lsmod | grep -Ei 'uvc|video|xhci|usb'"],['modinfo','uvcvideo']]
for p in sorted(Path('/dev').glob('video*')):commands.append(['v4l2-ctl','-d',str(p),'--list-formats-ext'])
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'video_devices':videos,'commands':{' '.join(a):run(a) for a in commands},'tools':{x:shutil.which(x) for x in ['gst-launch-1.0','gst-inspect-1.0','v4l2-ctl','ffplay','xdputil','python3']},'models':{str(p):[x.name for x in p.iterdir()] if p.exists() else [] for p in [Path('/usr/share/vitis_ai_library/models'),Path('/usr/share/vitis_ai_library/samples'),Path('/home/root/aura')]}}))
